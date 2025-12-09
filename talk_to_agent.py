import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from llms.base_classes.chatmodel import EinsteinChatModel
from langchain_core.tools import tool 


def talk_to_agent(query: str):
    """Talk to the agent."""

    # Initialize the Einstein model
    model = EinsteinChatModel(api_key="sample", disable_streaming=True)

    # Create agent with NO tools
    agent = create_react_agent(model, tools=[]) 

    result = agent.invoke({
        "messages": [HumanMessage(content=query)]
    })

    return result['messages'][-1].content


query  = "How many floors does Salesforce B3 Tower in Hyderabad have?\n"
response = talk_to_agent(query)

print(f"\nQuery: \n{query}")
print(f"Response: \n{response}\n")