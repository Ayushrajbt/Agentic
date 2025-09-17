#!/usr/bin/env python3
"""
Flask Web API for Evolyn Conversational Agent
Simple web interface that exposes the conversational agent through HTTP endpoints.
"""

from flask import Flask, request, jsonify
import logging
from app import create_agent, chat_with_agent

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
        "account_id": "optional account ID for context",
        "facility_id": "optional facility ID for context",
        "conversation_history": [optional array of previous messages]
    }
    
    Returns:
    {
        "response": "Agent response",
        "conversation_history": [updated conversation history],
        "account_id": "account ID if provided",
        "facility_id": "facility ID if provided",
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
        
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No JSON data provided",
                "status": "error"
            }), 400
        
        # Extract message
        message = data.get('message', '').strip()
        if not message:
            return jsonify({
                "error": "Message is required",
                "status": "error"
            }), 400
        
        # Extract account_id and facility_id (optional)
        account_id = data.get('account_id', '').strip()
        facility_id = data.get('facility_id', '').strip()
        
        # Get conversation history (optional)
        conversation_history = data.get('conversation_history', [])
        
        # Add context to message if account_id or facility_id is provided
        context_parts = []
        if account_id:
            context_parts.append(f"Account Context: {account_id}")
        if facility_id:
            context_parts.append(f"Facility Context: {facility_id}")
        
        if context_parts:
            contextual_message = f"[{', '.join(context_parts)}] {message}"
        else:
            contextual_message = message
        
        # Chat with agent
        result = chat_with_agent(agent, contextual_message, conversation_history, account_id, facility_id)
        
        # Return response with context IDs
        response_data = {
            "response": result["response"],
            "conversation_history": result["conversation_history"],
            "status": "success"
        }
        
        # Include account_id and facility_id in response if provided
        if account_id:
            response_data["account_id"] = account_id
        if facility_id:
            response_data["facility_id"] = facility_id
        
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
            "conversation_history": []
        },
        "example_response": {
            "response": "Here are the facility details...",
            "conversation_history": [
                {"role": "user", "content": "Show me facility details"},
                {"role": "assistant", "content": "Here are the facility details..."}
            ],
            "facility_id": "F-123456",
            "account_id": "A-011977763",
            "status": "success"
        },
        "payload_fields": {
            "message": "Required: Your question or request",
            "account_id": "Optional: Account ID for context and future features",
            "facility_id": "Optional: Facility ID for context and future features",
            "conversation_history": "Optional: Array of previous messages for conversation continuity"
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
                "account_id": "Optional account ID for context",
                "facility_id": "Optional facility ID for context",
                "conversation_history": "Optional array of previous messages"
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
