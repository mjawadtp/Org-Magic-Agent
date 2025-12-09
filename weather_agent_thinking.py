#!/usr/bin/env python3
"""
Weather Agent Demo - Build An Agent Learning Module

Simple demonstration for building an agent with weather tools.
Follow the step-by-step guide in STEP_BY_STEP_GUIDE.md

Run with: python examples/weather_agent_demo.py
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langgraph.prebuilt import create_react_agent
    
    # Import our custom model
    from llms.base_classes.chatmodel import EinsteinChatModel
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed: poetry install")
    sys.exit(1)

# Define weather tool
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
        "seattle": "Overcast, 60°F (15°C), Light drizzle",
        "chicago": "Windy, 68°F (20°C), Strong gusts"
    }
    
    city_lower = city.lower()
    if city_lower in weather_data:
        return f"Current weather in {city}: {weather_data[city_lower]}"
    else:
        return f"Weather data not available for {city}. Available cities: San Francisco, New York, London, Tokyo, Seattle, Chicago"

def run_agent_with_thinking(agent_executor, query, query_number=1):
    """
    Run the agent with a query and display the thinking process.
    
    Args:
        agent_executor: The configured agent executor
        query: The user query string
        query_number: Optional number for display purposes
    
    Example:
        agent = create_react_agent(model, tools)
        run_agent_with_thinking(agent, "What's the weather in Tokyo?")
        run_agent_with_thinking(agent, "Compare weather in Paris and London", 2)
    """
    try:
        print(f"👤 User Query: {query}")
        print("\n🧠 Agent Thinking Process:")
        print("-" * 40)
        
        # Stream to show the agent's thinking process
        config = {"configurable": {"thread_id": f"demo-{query_number}"}}
        tool_call_count = 0
        processed_messages = 0
        
        for step in agent_executor.stream({
            "messages": [HumanMessage(content=query)]
        }, config, stream_mode="values"):
            
            messages = step.get("messages", [])
            if messages:
                # Process all new messages, not just the latest
                new_messages = messages[processed_messages:]
                processed_messages = len(messages)
                
                for message in new_messages:
                    # Check message type properly
                    if isinstance(message, HumanMessage):
                        print(f"👤 Human: {message.content}")
                        
                    elif isinstance(message, AIMessage):
                        if message.tool_calls:
                            # Show all tool calls if there are multiple
                            for j, tool_call in enumerate(message.tool_calls):
                                tool_call_count += 1
                                print(f"🔧 Agent calls tool #{tool_call_count}: {tool_call['name']}")
                                print(f"   With arguments: {tool_call['args']}")
                        else:
                            print(f"💭 Agent responds: {message.content}")
                            
                    elif isinstance(message, ToolMessage):
                        print(f"📊 Tool result: {message.content}")
        
        print(f"\n✅ Query {query_number} completed!")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")

def main():
    """Run the weather agent demonstration."""
    print("🌦️  Weather Agent Demonstration")
    print("=" * 60)
    print("Follow the step-by-step guide in STEP_BY_STEP_GUIDE.md")
    print("=" * 60)
    
    # Check environment
    required_vars = ["EINSTEIN_GATEWAY_SERVER", "EINSTEIN_GATEWAY_PATH", "EINSTEIN_CHAT_MODEL_NAME"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set up your .env file with Einstein configuration.")
        return
    
    try:
        # Initialize the model and create agent
        model = EinsteinChatModel(api_key="sample", disable_streaming=True)
        tools = [get_weather]
        agent_executor = create_react_agent(model, tools)
        
        # Test multiple queries
        test_queries = [
            "What's the weather like in San Francisco?",
            "Is it raining in London right now?",
            "Should I bring a jacket in New York today?",
            "Compare the weather in Tokyo and Seattle",
            "What's the weather in Paris?" # This will test unknown city handling
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'='*60}")
            print(f"🌦️  TEST QUERY {i}")
            print(f"{'='*60}")
            
            # Run the agent with thinking display
            run_agent_with_thinking(agent_executor, query, i)
        
        print(f"\n{'='*60}")
        print("🎉 All test queries completed!")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Please check your configuration and follow the step-by-step guide.")

if __name__ == "__main__":
    main() 