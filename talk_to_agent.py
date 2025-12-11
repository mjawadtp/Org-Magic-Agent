import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from llms.base_classes.chatmodel import EinsteinChatModel
from langchain_core.tools import tool
from metadata_processor import get_metadata_information
from org_utils import deploy_metadata
from langchain_core.messages import AIMessage

# System instructions for the agent
SYSTEM_INSTRUCTIONS = (
    "I am building an application to automatically generate metadata XML files to be deployed "
    "in a Salesforce org. I want you to generate metadata XML files as requested in the prompt "
    "that will follow. Prompts are entered by users based on which we generate XML files. "
    "Generate ONLY the XML file since I need to process it. Remove markdown characters if any. Also, after generating the XML file, "
    "crosscheck with Salesforce metadata definition (XSD) and metadata information that will follow to ensure that all the required fields "
    "are available so that the deploy does not fail. For the fields, use relevant random names unless specified by the user. "  
    "Make sure that all fields have sensible values in them that make sense with respect to each other. "
    "For a new custom object, add 'label' and add 'nameField' with a field name as 'Reference number' as type AutoNumber . "
    "If the user wants to create settings, it refers to settings Metadata like SurveySettings, IndustriesSettings, etc, NOT a CustomObject!"
    "IMPORTANT: You have access to the full conversation history. When a user asks to modify a previously generated XML (e.g., 'modify the XML's name field' or 'change the URL in the last XML'), "
    "you should look at the conversation history to find the most recent XML output and modify it according to the user's request. "
    "The conversation history contains all previous user inputs and your outputs, so you can reference and modify previous XMLs. "
    "If multiple XML files are in the conversation, consider the most recent one unless the user specifies otherwise. "
    "Use the tool get_metadata_information to get metadata information about the metadata that the user wants to generate an XML for, if the information is available. "
    "You can also use the deploy_metadata tool to deploy generated XML files to the Salesforce org."
)


def talk_to_agent(query: str, system_instructions: str = None):
    """Talk to the agent.
    
    Args:
        query: The user's query/request
        system_instructions: Optional system instructions. If not provided, uses default SYSTEM_INSTRUCTIONS.
    """

    # Initialize the Einstein model
    model = EinsteinChatModel(api_key="sample", disable_streaming=True)

    # Create agent with metadata information tool
    agent = create_react_agent(model, tools=[get_metadata_information]) 

    # Prepare messages with system instructions
    messages = []
    
    # Add system message if instructions are provided
    if system_instructions:
        messages.append(SystemMessage(content=system_instructions))
    elif SYSTEM_INSTRUCTIONS:
        messages.append(SystemMessage(content=SYSTEM_INSTRUCTIONS))
    
    # Add user message
    messages.append(HumanMessage(content=query))

    result = agent.invoke({
        "messages": messages
    })

    return result['messages'][-1].content


def interactive_chat():
    """Interactive chat loop - like a Slack bot in the terminal."""
    print("=" * 60)
    print("🤖 OrgMagic Agent - Interactive Chat")
    print("=" * 60)
    print("Type your questions or requests. Type 'exit', 'quit', or 'bye' to end the chat.\n")
    
    # Initialize the model and agent once (more efficient)
    model = EinsteinChatModel(api_key="sample", disable_streaming=True)
    agent = create_react_agent(model, tools=[get_metadata_information, deploy_metadata])
    
    # Conversation history
    conversation_messages = []
    
    # Add system message to conversation
    conversation_messages.append(SystemMessage(content=SYSTEM_INSTRUCTIONS))
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'bye', 'q']:
                print("\n👋 Goodbye! Thanks for using OrgMagic Agent!")
                break
            
            # Skip empty input
            if not user_input:
                continue
            
            # Add user message to conversation
            conversation_messages.append(HumanMessage(content=user_input))
            
            # Get response from agent
            print("🤔 Thinking...")
            result = agent.invoke({
                "messages": conversation_messages
            })
            
            # IMPORTANT: LangGraph returns ALL messages (including tool calls and tool results)
            # The result['messages'] contains the full conversation history with new messages appended
            # We should use the returned messages as our new conversation state
            # This ensures the agent has access to:
            # - All previous user inputs
            # - All previous agent outputs (including XMLs)
            # - All tool calls and their results
            conversation_messages = result['messages']
            
            # Get the agent's final response (last message is usually the AI response)
            # Filter for the last AIMessage (agent's response, not tool calls)
            agent_responses = [msg for msg in conversation_messages if isinstance(msg, AIMessage)]
            if agent_responses:
                agent_response = agent_responses[-1].content
            else:
                # Fallback: get last message content
                agent_response = conversation_messages[-1].content if conversation_messages else "No response"
            
            # Display response
            print(f"\n🤖 Agent: {agent_response}\n")
            print("-" * 60)
            
            # Debug: Show conversation length (optional, can remove later)
            # print(f"[Debug: Conversation has {len(conversation_messages)} messages]")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Thanks for using OrgMagic Agent!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again or type 'exit' to quit.\n")


if __name__ == "__main__":
    # Run interactive chat
    interactive_chat()
    
    # Uncomment below for one-off queries instead of interactive mode
    # user_input = "Can you create a remotesitesetting XML with url google.com and is active"
    # response = talk_to_agent(user_input)
    # print(f"\nUser Input: \n{user_input}\n")
    # print(f"Response: \n\n{response}\n")