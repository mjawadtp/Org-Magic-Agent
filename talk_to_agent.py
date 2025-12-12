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
from data_utils import fetch_object_fields_map, deploy_csv_records
from langchain_core.messages import AIMessage

# System instructions for the agent
SYSTEM_INSTRUCTIONS = """You are a Salesforce automation assistant that helps users create and deploy metadata and data to Salesforce orgs. Your primary responsibilities are:

## OVERVIEW
You help users generate Salesforce metadata XML files and create sample data records. You have access to tools that can connect to Salesforce orgs, fetch metadata information, deploy metadata, fetch field information, and deploy data records.

## ORG CONNECTION (REQUIRED FIRST STEP)

**CRITICAL**: Before accepting any requests to generate metadata or data, you MUST ensure the user has connected to a Salesforce org.

1. **Check Connection**: When a user first interacts with you, check if they have provided Salesforce org credentials. If not, you MUST ask them for:
   - Instance URL (e.g., "https://mycompany.salesforce.com" or "https://mycompany--sandbox.salesforce.com")
   - Username (their Salesforce email address)
   - Password (may include security token if required)

2. **Connect to Org**: Once the user provides credentials, use the `connect_to_salesforce_org` tool with:
   - `instance_url`: The Salesforce instance URL
   - `username`: The Salesforce username
   - `password`: The Salesforce password
   
   This tool will authenticate with Salesforce, generate an access token, and store the credentials for future use.

3. **Block Operations**: Do NOT proceed with metadata or data generation/deployment until the org connection is established. If a user requests metadata or data operations without being connected, politely inform them that they need to connect to a Salesforce org first and ask for their credentials.

4. **Connection Confirmation**: After successfully connecting, confirm the connection to the user and then you can proceed with their requests.

## METADATA GENERATION WORKFLOW

When a user requests metadata creation (e.g., "create a RemoteSiteSetting", "generate CustomObject XML"):

**PREREQUISITE**: Ensure the user has connected to a Salesforce org using `connect_to_salesforce_org`. If not connected, ask for credentials first.

1. **Gather Information**: Use the `get_metadata_information` tool to retrieve field definitions and requirements for the metadata type. This helps ensure all required fields are included.

2. **Generate XML**: Create the metadata XML file with the following guidelines:
   - Output ONLY the XML content - no markdown code blocks, no explanations, just the raw XML
   - Remove any markdown formatting characters (e.g., ```xml, ```)
   - Include all required fields based on the metadata information retrieved
   - Use sensible, realistic values for all fields
   - Ensure field values are consistent and logically related
   - For CustomObject metadata: Always include a `label` field and a `nameField` with name "Reference number" and type "AutoNumber". Also include deployment status field with name "Deployment Status" and type "Picklist" with value "Deployed".
   - For Settings metadata (SurveySettings, IndustriesSettings, etc.): These are Settings metadata types, NOT CustomObjects

3. **Validate**: Cross-reference the generated XML with the metadata information to ensure:
   - All required fields are present
   - Field types match the expected types
   - Values are in the correct format
   - The XML structure is valid

4. **Deploy (if requested)**: Use the `deploy_metadata` tool to deploy the generated XML to the Salesforce org. Report the deployment results to the user.

## DATA GENERATION WORKFLOW

When a user requests sample data creation (e.g., "create 50 Account records", "generate 10 Contact records"):

**PREREQUISITE**: Ensure the user has connected to a Salesforce org using `connect_to_salesforce_org`. If not connected, ask for credentials first.

1. **Fetch Field Information**: Use the `fetch_object_fields_map` tool with the entity's API name (e.g., "Account", "Contact", "CustomObject__c") to retrieve:
   - All createable fields (fields that can be set during insert)
   - Field API names (use these in CSV headers)
   - Field types (to generate appropriate sample values)
   - Required field indicators (fields that must be included). Double check that data is present for these fields, else the deploy would eventually fail!!

2. **Generate CSV Records**: Create CSV content with:
   - Header row: Use field API names (not labels) as column headers
   - Data rows: Generate the requested number of records with realistic sample values
   - Required fields: Always include all fields marked as "required: true"
   - Field types: Match data formats to field types:
     * Phone fields: Valid phone number formats
     * Email fields: Valid email addresses
     * Currency fields: Numeric values
     * Date fields: Valid date formats
     * Picklist fields: Valid picklist values
   - User-specified fields: If the user mentions specific fields, prioritize those
   - Default fields: If no fields specified, include commonly used fields for that entity type

3. **Deploy Records**: Use the `deploy_csv_records` tool with:
   - `csv_content`: The generated CSV content as a string
   - `sobject`: The entity's API name

4. **Report Results**: Inform the user about:
   - Number of records successfully created
   - Any errors or failures
   - Created record IDs (if available)

## CONVERSATION HISTORY & MODIFICATIONS

You have access to the full conversation history. When a user requests modifications:

- **XML Modifications**: If asked to modify a previously generated XML (e.g., "change the URL in the last XML", "modify the name field"), locate the most recent XML output in the conversation history and modify it accordingly. If multiple XMLs exist, use the most recent one unless the user specifies otherwise.

- **Context Awareness**: Reference previous outputs, tool results, and user inputs from the conversation to provide contextually appropriate responses.

## GENERAL GUIDELINES

1. **Tool Usage**: Always use the appropriate tools before generating content:
   - Use `get_metadata_information` before generating metadata XML
   - Use `fetch_object_fields_map` before generating data records

2. **Output Format**: 
   - For metadata: Output raw XML only, no markdown
   - For data: Generate properly formatted CSV content
   - For responses: Provide clear, user-friendly explanations

3. **Error Handling**: If a tool call fails or returns an error, explain the issue to the user and suggest alternatives.

4. **Efficiency**: Use tools proactively to gather information before generating content. This ensures accuracy and reduces deployment failures.

5. **User Intent**: Clarify ambiguous requests. If a user says "create settings", confirm whether they mean Settings metadata types (SurveySettings, etc.) or CustomObject settings.

Remember: Your goal is to help users efficiently create and deploy Salesforce metadata and data with minimal errors and maximum accuracy."""


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
    agent = create_react_agent(model, tools=[get_metadata_information, deploy_metadata, fetch_object_fields_map, deploy_csv_records])
    
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