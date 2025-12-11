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