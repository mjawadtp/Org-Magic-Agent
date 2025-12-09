#!/usr/bin/env python3
import sys
import os
import requests

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from llms.base_classes.chatmodel import EinsteinChatModel
from langchain_core.tools import tool  # ADD this import

# ADD this tool function:
@tool
def get_weather(city: str) -> str:
    """Get current weather information for a city.

    Args:
        city: Name of the city to get weather for

    Returns:
        Weather information for the specified city
    """
    # Mock weather data for demonstration
    weather_data = {
        "san francisco": "Cloudy, 65°F (18°C), Light fog expected",
        "new york": "Partly sunny, 72°F (22°C), Clear skies",
        "london": "Rainy, 58°F (14°C), Heavy rainfall",
        "tokyo": "Sunny, 75°F (24°C), Perfect weather",
    }

    city_lower = city.lower()
    if city_lower in weather_data:
        return f"Current weather in {city}: {weather_data[city_lower]}"
    else:
        return f"Weather data not available for {city}."


@tool
def fetch_object_fields_map(sobject: str) -> dict:
    """Return label->type map for a Salesforce object's describe."""
    query_url = (
        "https://dxx0000006gqxeae.my.salesforce-com.6tjzv89xptfi0hqivm620yn4g1li1qk.ab.crm.dev:6101"
        f"/services/data/v66.0/sobjects/{sobject}/describe/"
    )

    headers = {
        # Replace with a valid token before running.
        "Authorization": "Bearer 00Dxx0000006GqxEAE!AQEAQO0vjnNAJXYYhfZb6N_aUEWQ3GRkJyjC5fjAsbYHlYrQ70wXZ7sIxRUeNawdEEZ4F3zAwV25U3ZjrAwZqQrN9WzdRacY",
        "Content-Type": "application/json",
    }

    response = requests.get(query_url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    return {
        field["label"]: field.get("type")
        for field in data.get("fields", [])
        if (
            not field.get("nillable", True)
            and field.get("updateable", False)
            and field.get("createable", False)
            and not field.get("defaultedOnCreate", False)
        )
    }


def main():
    """Test our weather agent."""

    # Initialize the Einstein model
    model = EinsteinChatModel(api_key="sample", disable_streaming=True)

    # Create agent with NO tools
    agent = create_react_agent(model, tools=[get_weather])  # Empty tools list

    query = "What's the weather like in San Francisco?"
    # Ask the agent our question
    result = agent.invoke({
        "messages": [HumanMessage(content=query)]
    })

    print("\n")

    print(result)

    # Get the agent's response
    response = result['messages'][-1].content
    print(f"🤖 Agent Response: {response}")

if __name__ == "__main__":
    main()