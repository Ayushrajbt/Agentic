#!/usr/bin/env python3
"""
Flask Web API for Evolyn Conversational Agent
Simple web interface that exposes the conversational agent through HTTP endpoints.
"""

from flask import Flask, request, jsonify
import logging
from app import create_agent, chat_with_agent
from conversation_service import conversation_service
from models import ChatRequest
from pydantic import ValidationError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Global agent instance (created once on startup)
agent = None

def initialize_agent():
    """Initialize the agent on startup."""
    global agent
    try:
        logger.info("🤖 Initializing conversational agent...")
        agent = create_agent()
        logger.info("✅ Agent initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "agent_ready": agent is not None,
        "message": "Evolyn Conversational Agent API is running"
    })

@app.route('/chat', methods=['POST'])
def chat():
    """
    Chat endpoint that accepts messages and returns agent responses.
    
    Expected JSON payload:
    {
        "message": "Your message here",
        "account_id": "account ID for context (required if facility_id not provided)",
        "facility_id": "facility ID for context (required if account_id not provided)",
        "user_id": "user ID (email) - required for all requests",
        "conversation_id": "optional conversation ID to continue existing conversation"
    }
    
    Returns:
    {
        "response": "Agent response",
        "conversation_id": "conversation ID for future requests",
        "account_id": "account ID if provided",
        "facility_id": "facility ID if provided",
        "user_id": "user ID if provided",
        "status": "success"
    }
    """
    try:
        # Check if agent is initialized
        if agent is None:
            return jsonify({
                "error": "Agent not initialized",
                "status": "error"
            }), 500
        
        # Validate request using Pydantic
        try:
            request_data = ChatRequest(**request.get_json())
        except ValidationError as e:
            return jsonify({
                "error": str(e),
                "status": "error"
            }), 400
        
        # Extract validated data
        message = request_data.message.strip()
        account_id = request_data.account_id.strip() if request_data.account_id else ''
        facility_id = request_data.facility_id.strip() if request_data.facility_id else ''
        user_id = request_data.user_id.strip() if request_data.user_id else ''
        conversation_id = request_data.conversation_id.strip() if request_data.conversation_id else ''
        
        # Get conversation history from database or initialize empty
        conversation_history = []
        if conversation_id:
            # Try to get existing conversation
            conversation = conversation_service.get_conversation(conversation_id)
            if conversation:
                conversation_history = conversation['conversation_history']
            else:
                return jsonify({
                    "error": f"Conversation with ID {conversation_id} not found",
                    "status": "error"
                }), 404
        
        # Add context to message if account_id, facility_id, or user_id is provided
        context_parts = []
        if account_id:
            context_parts.append(f"Account Context: {account_id}")
        if facility_id:
            context_parts.append(f"Facility Context: {facility_id}")
        if user_id:
            context_parts.append(f"User Context: {user_id}")
        
        if context_parts:
            contextual_message = f"[{', '.join(context_parts)}] {message}"
        else:
            contextual_message = message
        
        # Chat with agent
        result = chat_with_agent(agent, contextual_message, conversation_history, account_id, facility_id, user_id)
        
        # Get updated conversation history from the agent's internal state
        # We need to reconstruct this from the conversation_history we passed in + the new exchange
        updated_conversation_history = conversation_history.copy()
        updated_conversation_history.append({"role": "user", "content": contextual_message})
        
        # Handle both old and new response formats
        response_text = result.get("final_response", result.get("response", "I'm not sure how to respond to that."))
        updated_conversation_history.append({"role": "assistant", "content": response_text})
        
        if conversation_id:
            # Update existing conversation
            success = conversation_service.update_conversation(conversation_id, updated_conversation_history)
            if not success:
                logger.warning(f"Failed to update conversation {conversation_id}")
        else:
            # Create new conversation
            conversation_id = conversation_service.create_conversation(
                updated_conversation_history, 
                account_id if account_id else None, 
                facility_id if facility_id else None
            )
                
        # Start with basic response fields
        response_data = {
            "final_response": result.get("final_response", "I'm not sure how to respond to that."),
            "conversation_id": conversation_id,
            "status": "success"
        }

        if result.get("message"):
            response_data["message"] = result.get("message")


        # Include structured data only for overview queries
        response_type = result.get("response_type", "conversational")
        if response_type in ["account_overview", "facility_overview", "notes_overview"]:
            response_data["response_type"] = response_type
            
            # Only include non-null structured fields
            if result.get("account_details"):
                response_data["account_details"] = result.get("account_details")
            if result.get("facility_details"):
                response_data["facility_details"] = result.get("facility_details")
            if result.get("notes_data"):
                response_data["notes_data"] = result.get("notes_data")

        # Include account_id, facility_id, and user_id in response if provided
        if account_id:
            response_data["account_id"] = account_id
        if facility_id:
            response_data["facility_id"] = facility_id
        if user_id:
            response_data["user_id"] = user_id

        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "status": "error"
        }), 500

@app.route('/chat', methods=['GET'])
def chat_info():
    """Get information about the chat endpoint."""
    return jsonify({
        "endpoint": "/chat",
        "methods": ["POST"],
        "description": "Send messages to the conversational agent",
        "example_request": {
            "message": "Show me facility details",
            "facility_id": "F-123456",
            "account_id": "A-011977763",
            "user_id": "user@example.com",
            "conversation_id": "optional-existing-conversation-id"
        },
        "example_response": {
            "response": "Here are the facility details...",
            "conversation_id": "new-or-updated-conversation-id",
            "facility_id": "F-123456",
            "account_id": "A-011977763",
            "user_id": "user@example.com",
            "status": "success"
        },
        "payload_fields": {
            "message": "Required: Your question or request",
            "account_id": "Required: Account ID for context (if facility_id not provided)",
            "facility_id": "Required: Facility ID for context (if account_id not provided)",
            "user_id": "Required: User ID (email) for all requests",
            "conversation_id": "Optional: Conversation ID to continue existing conversation"
        },
        "validation_rules": {
            "user_id": "Always required - cannot be empty",
            "account_id_or_facility_id": "At least one must be provided - both cannot be empty"
        }
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "name": "Evolyn Conversational Agent API",
        "version": "1.0.0",
        "description": "A conversational AI agent for querying Evolyn database",
        "endpoints": {
            "/": "This information page",
            "/health": "Health check",
            "/chat": "Chat with the agent (POST) or get info (GET)"
        },
        "usage": {
            "chat_endpoint": "POST /chat",
            "payload": {
                "message": "Your question or request",
                "account_id": "Account ID for context (required if facility_id not provided)",
                "facility_id": "Facility ID for context (required if account_id not provided)",
                "user_id": "User ID (email) - required for all requests",
                "conversation_id": "Optional conversation ID to continue existing conversation"
            },
            "validation_rules": {
                "user_id": "Always required - cannot be empty",
                "account_id_or_facility_id": "At least one must be provided - both cannot be empty"
            }
        },
        "examples": [
            "Show me account details for Dimod Account",
            "Find facilities for account A-011977763",
            "Show me details for facility F-123456",
            "What are the database statistics?",
            "Show me all active facilities"
        ]
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "status": "error",
        "available_endpoints": ["/", "/health", "/chat"]
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        "error": "Method not allowed",
        "status": "error"
    }), 405

if __name__ == '__main__':
    # Initialize agent on startup
    if not initialize_agent():
        logger.error("Failed to initialize agent. Exiting.")
        exit(1)
    
    # Run Flask app
    logger.info("🚀 Starting Evolyn Conversational Agent API on http://localhost:5050")
    logger.info("📖 Available endpoints:")
    logger.info("  GET  / - API information")
    logger.info("  GET  /health - Health check")
    logger.info("  GET  /chat - Chat endpoint info")
    logger.info("  POST /chat - Send messages to agent")
    
    app.run(host='0.0.0.0', port=5050, debug=True)