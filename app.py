import os
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from tools import fetch_account_details, fetch_facility_details, save_note, get_notes
from database import db
from models import AgentStructuredResponse
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_agent():
    """Create and return the conversational agent."""
    # Test database connection
    if not db.test_connection():
        logger.error("Database connection failed!")
        raise Exception("Database connection failed! Please check your .env file and database settings.")
    
    # Initialize ChatGPT model
    model = init_chat_model(
        "openai:gpt-4o-mini",  # or "openai:gpt-3.5-turbo" for cheaper option
        temperature=0
    )

    # Create the agent with database tools and structured output
    structured_output_prompt = """
MANDATE: DO NOT OMIT, ALTER, OR ADD TO ANY TOOL OR AGENT RESPONSE.

    CRITICAL RULES:
    1. Response Preservation:
    - Return responses exactly as received — no rewording, summarizing, or formatting changes.
    - Every value, field, and character must be present.
    - DO NOT add, remove, paraphrase, truncate, or modify any content.
    - A single missing or altered value is a critical failure.

    2. Response Type Classification:
    - Set response_type to "account_overview" ONLY when user explicitly asks for "overview", "details", "summary", or "complete account information"
    - Set response_type to "facility_overview" ONLY when user explicitly asks for "overview", "details", or "summary" for facilities
    - Set response_type to "notes_overview" ONLY when user explicitly asks for notes or note summaries
    - Set response_type to "conversational" for ALL other queries including simple questions like "is my account active?", "what's my status?", "what's my balance?"

    3. CRITICAL FACILITY ID FALLBACK:
    - If user asks for a specific facility ID that doesn't exist or doesn't match context, respond with: "Sorry, I don't have information for the Facility ID provided by user"
    - DO NOT return information for a different facility just because it exists in the context
    - Always prioritize the specific facility ID mentioned by the user over context facility_id

    4. Structured Data Population:
    - When response_type is "account_overview": Populate account_details with the complete AccountResponse data from fetch_account_details tool
    - When response_type is "facility_overview": Populate facility_details with the complete FacilityResponse data from fetch_facility_details tool
    - When response_type is "notes_overview": Populate notes_data with the complete NotesListResponse data from get_notes tool
    - When response_type is "conversational": Leave account_details, facility_details, and notes_data as null
    - For specific note requests (e.g., "second last note"), set response_type to "notes_overview" and populate notes_data
    - When handling specific note requests, fetch notes with limit=10 to ensure you have enough notes to select from, then select the appropriate note from the results  
    
    4. Message:
    - Populate message with the response content in bullet points
    
    5. Tool Response Handling:
    - Parse tool responses as JSON and populate the appropriate structured field
    - Do NOT modify tool response data - use it exactly as received
    - If tool returns error, still populate the structured field with the error response

    6. Format:
    - Preserve original structure, layout, and whitespace.
    - Output must be valid and match the expected schema.

    7. When the user sends messages containing inappropriate, offensive, or hate speech:
    - Respond with: "Apologies, but I wasn't able to locate the information requested."
    - Do not engage further.

    FAILURE TO FOLLOW THESE RULES WILL BREAK SYSTEM FUNCTIONALITY.
    """
    agent = create_react_agent(
        model=model,
        tools=[fetch_account_details, fetch_facility_details, save_note, get_notes],
        prompt="""You are a helpful database assistant for the Evolyn system. You can help users:
1. Fetch account details by account ID or name
2. Fetch facility details by facility ID, name, or account ID
3. Save notes for accounts or facilities (use save_note tool - note content, user_id, and either account_id or facility_id are automatically provided from context)
4. Retrieve notes for accounts or facilities (use get_notes tool - user_id and either account_id or facility_id are automatically provided from context)

CROSS-REFERENCE INTELLIGENCE:
- When user asks for account information but only facility_id is provided in context, the fetch_account_details tool will automatically get the account_id from the facility
- When user asks for facility information but only account_id is provided in context, the fetch_facility_details tool will get facilities for that account
- The tools are smart enough to handle cross-references automatically - you don't need to manually resolve them

CRITICAL FACILITY ID HANDLING:
- When a user asks for information about a SPECIFIC facility ID (e.g., "Show me facility F-123456", "Fetch me facility details of F-123456"), you MUST use that exact facility ID
- If the user mentions a specific facility ID that doesn't exist or doesn't match the context facility_id, respond with: "Sorry, I don't have information for the Facility ID provided by user"
- DO NOT return information for a different facility just because it exists in the context
- Always prioritize the specific facility ID mentioned by the user over the context facility_id

RESPONSE TYPE CLASSIFICATION:
- Set response_type to "account_overview" ONLY when users explicitly use words like "overview", "details", "summary", "complete account information" (e.g., "show me account overview", "give me account details", "account summary", "fetch me account overview", "complete account information")
- Set response_type to "facility_overview" ONLY when users explicitly use words like "overview", "details", "summary" for facilities (e.g., "show me facility overview", "give me facility details", "facility summary")
- Set response_type to "notes_overview" ONLY when users explicitly ask for notes, note summaries, or specific notes (e.g., "second last note", "third note", "last note")
- Set response_type to "conversational" for ALL other queries including:
  * Simple questions like "what's my account status?", "is my account active?", "what's my balance?", "when is my invoice due?"
  * Specific questions about individual properties without asking for "overview" or "details"
  * General conversation and questions that don't explicitly request overviews or complete details

IMPORTANT: Only fetch information that the user specifically asks for. If they ask for "account overview", only fetch account details. If they ask for "facility overview", only fetch facility details.

For note operations:
- When users say "Save this note: [content]", extract ONLY the content part (after "Save this note:") and pass it to the save_note tool
- When users ask for notes, use get_notes tool (all required parameters are automatically provided from context)
- The system automatically provides user_id, account_id, and facility_id from the conversation context
- For save_note tool: pass the extracted note content (without "Save this note:" prefix) as note_content
- When users ask for specific notes like "second last note", "third note", "last note", etc., use get_notes tool to fetch all notes and then select the appropriate one from the results
- For ordinal requests (second last, third, etc.), fetch notes with a higher limit (e.g., 10) to ensure you have enough notes to select from

When account_id, facility_id, or user_id context is provided in the message, use that information to help answer
questions more effectively, but only fetch the specific information requested.

Be helpful and provide clear, formatted responses. When users ask about accounts or facilities, 
use the appropriate tools to fetch the information from the database.""",
        response_format=(structured_output_prompt, AgentStructuredResponse)
    )
    
    return agent

def chat_with_agent(agent, message, conversation_history=None, account_id=None, facility_id=None, user_id=None):
    """Chat with the agent and return the response."""
    try:
        # Initialize conversation state
        if conversation_history is None:
            conversation_state = {"messages": []}
        else:
            # Convert any LangChain message objects back to dict format
            clean_history = []
            for msg in conversation_history:
                if isinstance(msg, dict):
                    clean_history.append(msg)
                else:
                    # Convert LangChain message objects to dict format
                    clean_history.append({
                        "role": getattr(msg, 'type', 'assistant').replace('human', 'user'),
                        "content": getattr(msg, 'content', str(msg))
                    })
            conversation_state = {"messages": clean_history}
        
        # Add context information if available
        context_message = ""
        if account_id:
            context_message += f"Account ID: {account_id}. "
        if facility_id:
            context_message += f"Facility ID: {facility_id}. "
        if user_id:
            context_message += f"User ID: {user_id}. "
        
        # Add user message with context to conversation state
        full_message = context_message + message if context_message else message
        conversation_state["messages"].append({"role": "user", "content": full_message})
        
        # Create RunnableConfig with context information
        config = {
            "configurable": {
                "account_id": account_id,
                "facility_id": facility_id,
                "user_id": user_id,
                "note_content": message  # Include the message for note operations
            }
        }
        
        # Get agent response with RunnableConfig
        result = agent.invoke(conversation_state, config=config)
        
        # Return the structured response from LLM
        if hasattr(result, 'structured_response') and result.structured_response:
            return result.structured_response.model_dump()
        elif isinstance(result, dict) and 'structured_response' in result:
            return result['structured_response'].model_dump()
        else:
            # This should never happen with structured output, but just in case
            raise Exception("Agent did not return structured response")
            
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        # Return a minimal error response
        return {
            "final_response": f"Sorry, I encountered an error: {e}",
            "response_type": "conversational",
            "conversation_id": None,
            "user_id": user_id,
            "message": None
        }
def main():
    """Main function to run the conversational agent."""
    print("🤖 Database Conversational Agent Started!")
    print("Type 'quit', 'exit', or 'bye' to end the conversation.")
    print("Available commands:")
    print("- Ask about accounts: 'Show me account details for account_id 123'")
    print("- Ask about facilities: 'Show me facilities for account ABC'")
    print("- Ask about specific facility: 'Show me facility details for facility_id F-123'")
    print("- Save notes: 'Save this note: [content]' (requires user_id and either account_id or facility_id)")
    print("- Get notes: 'Show me notes for this account/facility' (requires user_id and either account_id or facility_id)")
    print()
    print("ℹ️  Note: User ID (email) is required for all operations.")
    print()
    
    # Test database connection
    print("🔌 Testing database connection...")
    if db.test_connection():
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed! Please check your .env file and database settings.")
        return
    
    # Get user_id, account_id and facility_id from user
    print("📋 Please provide your user and account information:")
    
    # Get user_id (required)
    while True:
        user_id = input("User ID (email) - REQUIRED: ").strip()
        if user_id:
            print(f"✅ Using user ID: {user_id}")
            break
        else:
            print("❌ User ID is required. Please enter your email address.")
    
    # Get account_id or facility_id (at least one required)
    while True:
        account_id = input("Account ID (optional, press Enter to skip): ").strip()
        facility_id = input("Facility ID (optional, press Enter to skip): ").strip()
        
        if account_id or facility_id:
            if account_id:
                print(f"✅ Using account ID: {account_id}")
            if facility_id:
                print(f"✅ Using facility ID: {facility_id}")
            break
        else:
            print("❌ Either Account ID or Facility ID is required. Please provide at least one.")
    
    # Set None for empty values
    account_id = account_id if account_id else None
    facility_id = facility_id if facility_id else None
    
    print()
    
    # Create agent
    agent = create_agent()
    
    # Initialize conversation state
    conversation_state = {"messages": []}
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                print("🤖 Agent: Goodbye! It was nice chatting with you!")
                break
            
            # Skip empty inputs
            if not user_input:
                continue
            
            # Chat with agent
            result = chat_with_agent(agent, user_input, conversation_state["messages"], account_id, facility_id, user_id)
            
            # Handle both old and new response formats
            if "final_response" in result:
                response_text = result["final_response"]
                print("🤖 Agent:", response_text)
                # Update conversation state with the new exchange
                conversation_state["messages"].append({"role": "user", "content": user_input})
                conversation_state["messages"].append({"role": "assistant", "content": response_text})
            elif "response" in result:
                # Legacy format
                response_text = result["response"]
                print("🤖 Agent:", response_text)
                # Update conversation state with the new exchange
                conversation_state["messages"].append({"role": "user", "content": user_input})
                conversation_state["messages"].append({"role": "assistant", "content": response_text})
            else:
                print("🤖 Agent: I'm not sure how to respond to that.")
                conversation_state["messages"].append({"role": "user", "content": user_input})
                conversation_state["messages"].append({"role": "assistant", "content": "I'm not sure how to respond to that."})
            
            print()  # Add spacing between exchanges
            
        except KeyboardInterrupt:
            print("\n🤖 Agent: Goodbye! It was nice chatting with you!")
            break
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            print(f"🤖 Agent: Sorry, I encountered an error: {e}")
            print("Please try again.\n")

if __name__ == "__main__":
    main()