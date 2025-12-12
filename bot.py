from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import agent components
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from llms.base_classes.chatmodel import EinsteinChatModel
from metadata_processor import get_metadata_information
from org_utils import deploy_metadata
from data_utils import fetch_object_fields_map, deploy_csv_records
from org_connection import connect_to_salesforce_org, has_org_credentials
from talk_to_agent import SYSTEM_INSTRUCTIONS

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_APP_TOKEN = os.environ.get('SLACK_APP_TOKEN')

# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN)

# ============================================
# INITIALIZE AGENT (once at startup)
# ============================================
print("🤖 Initializing OrgMagic Agent...")
model = EinsteinChatModel(api_key="sample", disable_streaming=True)
agent = create_react_agent(
    model, 
    tools=[connect_to_salesforce_org, get_metadata_information, deploy_metadata, fetch_object_fields_map, deploy_csv_records]
)
print("✅ Agent initialized successfully!")

# ============================================
# CONVERSATION HISTORY STORAGE
# ============================================
# Single conversation history for all messages (single user support)
conversation_messages = [SystemMessage(content=SYSTEM_INSTRUCTIONS)]


@app.event("app_mention")
def mention_handler(body, say):
    """Handle when the bot is mentioned."""
    print(f"Mention event: {body}")
    say('Hello! I\'m the OrgMagic Agent. How can I help you with Salesforce metadata and data today?')


@app.event("message")
def respond_message(message, say):
    """Handle direct messages to the bot."""
    # Skip bot's own messages
    if message.get('subtype') == 'bot_message':
        return
    
    # Extract message information
    channel_id = message.get('channel')
    user_id = message.get('user')
    text = message.get('text', '').strip()
    event_ts = message.get('ts')
    thread_ts = message.get('thread_ts')
    
    # Skip empty messages
    if not text:
        return
    
    print(f"Message from {user_id} in {channel_id}: {text}")
    
    # Add thinking reaction
    try:
        app.client.reactions_add(channel=channel_id, name='eyes', timestamp=event_ts)
    except Exception as e:
        print(f"Warning: Failed to add :eyes: reaction: {e}")
    
    try:
        global conversation_messages
        
        # Add user message to conversation
        conversation_messages.append(HumanMessage(content=text))
        
        # Invoke agent (same pattern as interactive_chat)
        print("🤔 Agent thinking...")
        result = agent.invoke({
            "messages": conversation_messages
        })
        
        # Update conversation history with all messages (including tool calls and results)
        conversation_messages = result['messages']
        
        # Extract agent's final response
        agent_responses = [msg for msg in conversation_messages if isinstance(msg, AIMessage)]
        if agent_responses:
            agent_response = agent_responses[-1].content
        else:
            agent_response = conversation_messages[-1].content if conversation_messages else "No response"
        
        # Determine thread timestamp (reply in thread if it's a thread, otherwise create new thread)
        reply_thread_ts = thread_ts or event_ts
        
        # Send response back to Slack
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=reply_thread_ts,
            text=agent_response
        )
        
        print(f"✅ Response sent to {user_id}")
        
    except Exception as e:
        error_msg = f"❌ Error processing message: {str(e)}"
        print(error_msg)
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts or event_ts,
            text=error_msg
        )
    finally:
        # Remove thinking reaction
        try:
            app.client.reactions_remove(channel=channel_id, name='eyes', timestamp=event_ts)
        except Exception as e:
            print(f"Warning: Failed to remove :eyes: reaction: {e}")

if __name__=="__main__":
    handler=SocketModeHandler(app,SLACK_APP_TOKEN)
    handler.start()
