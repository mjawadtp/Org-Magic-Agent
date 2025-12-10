import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from llms.base_classes.chatmodel import EinsteinChatModel
from langchain_core.tools import tool
from metadata_processor import get_metadata_information 

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
    "In some cases, previously generated XML will be passed in the prompt. If multiple XML files are passed, consider only the last one. In such cases, make relevant modifications as requested in the XML file."
    "Use the tool get_metadata_information to get metadata information about the metadata that the user wants to generate an XML for, if the information is available"
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


user_input = "Can you create a remotesitesetting XML with url google.com and is active"

response = talk_to_agent(user_input)

print(f"\nUser Input: \n{user_input}\n")
print(f"Response: \n\n{response}\n")