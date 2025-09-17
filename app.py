import os
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from tools import fetch_account_details, fetch_facility_details, save_note, get_notes
from database import db
from models import SimpleResponse
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

    # Create the agent with database tools
    agent = create_react_agent(
        model=model,
        tools=[fetch_account_details, fetch_facility_details, save_note, get_notes],
        prompt="""You are a helpful database assistant for the Evolyn system. You can help users:
1. Fetch account details by account ID or name
2. Fetch facility details by facility ID, name, or account ID
3. Save notes for accounts (use save_note tool with note content and account_id)
4. Retrieve notes for accounts (use get_notes tool with account_id)

For note saving, when users say "Save this note: [content]" and an account_id is provided in the context,
use the save_note tool with the note content and account_id.

When account_id or facility_id context is provided in the message, use that information to help answer
questions more effectively. For example, if facility_id is provided, you can fetch facility details
or related account information to provide better context.

Be helpful and provide clear, formatted responses. When users ask about accounts or facilities, 
use the appropriate tools to fetch the information from the database."""
    )
    
    return agent

def chat_with_agent(agent, message, conversation_history=None, account_id=None, facility_id=None):
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
        
        # Add user message to conversation state
        conversation_state["messages"].append({"role": "user", "content": message})
        
        # Get agent response
        result = agent.invoke(conversation_state)
        
        # Extract the response message
        if "messages" in result and result["messages"]:
            # Get the last message from the agent
            last_message = result["messages"][-1]
            if isinstance(last_message, dict) and "content" in last_message:
                response_content = last_message["content"]
            else:
                # Extract content from LangChain message object
                response_content = getattr(last_message, 'content', str(last_message))
            
            # Convert conversation history to JSON-serializable format
            # Filter out tool messages as they can't be reused in conversation history
            serializable_history = []
            for msg in result["messages"]:
                if isinstance(msg, dict):
                    # Skip tool messages as they can't be reused
                    if msg.get("role") == "tool":
                        continue
                    serializable_history.append(msg)
                else:
                    # Convert LangChain message objects to dict format
                    msg_type = getattr(msg, 'type', 'assistant')
                    if hasattr(msg, 'type'):
                        role = msg.type.replace('human', 'user').replace('ai', 'assistant')
                    else:
                        role = 'assistant'
                    
                    # Skip tool messages
                    if role == "tool":
                        continue
                    
                    serializable_history.append({
                        "role": role,
                        "content": getattr(msg, 'content', str(msg))
                    })
            
            # Return structured response and updated conversation history
            return SimpleResponse(
                account_id=account_id,
                facility_id=facility_id,
                response=response_content,
                conversation_history=serializable_history
            ).model_dump()
        else:
            return SimpleResponse(
                account_id=account_id,
                facility_id=facility_id,
                response="I'm not sure how to respond to that.",
                conversation_history=conversation_state["messages"]
            ).model_dump()
            
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return SimpleResponse(
            account_id=account_id,
            facility_id=facility_id,
            response=f"Sorry, I encountered an error: {e}",
            conversation_history=conversation_state.get("messages", [])
        ).model_dump()

def main():
    """Main function to run the conversational agent."""
    print("🤖 Database Conversational Agent Started!")
    print("Type 'quit', 'exit', or 'bye' to end the conversation.")
    print("Available commands:")
    print("- Ask about accounts: 'Show me account details for account_id 123'")
    print("- Ask about facilities: 'Show me facilities for account ABC'")
    print("- Ask about specific facility: 'Show me facility details for facility_id F-123'")
    print("- Save notes: 'Save this note: [content]'")
    print("- Get notes: 'Show me notes for this account'")
    print()
    
    # Test database connection
    print("🔌 Testing database connection...")
    if db.test_connection():
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed! Please check your .env file and database settings.")
        return
    
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
            result = chat_with_agent(agent, user_input, conversation_state["messages"])
            
            print("🤖 Agent:", result["response"])
            conversation_state["messages"] = result["conversation_history"]
            
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