import asyncio
import os
from dotenv import load_dotenv
from routing_agent_langgraph import RoutingAgent

load_dotenv()

async def test_routing_agent():
    """Test the RoutingAgent initialization and message sending."""
    try:
        # Initialize RoutingAgent with remote agent addresses
        routing_agent = await RoutingAgent.create(
            remote_agent_addresses=[
                os.getenv('AIR_AGENT_URL', 'http://localhost:10002'),
                os.getenv('WEA_AGENT_URL', 'http://localhost:10001'),
            ]
        )
        print("RoutingAgent initialized successfully.")

        # Create the LangGraph agent
        agent_executor = routing_agent.create_agent()
        print("LangGraph agent created.")

        # Test sending a sample message
        sample_message = {
            "messages": [
                {"role": "user", "content": "Check the weather in New York"}
            ]
        }
        async for response in agent_executor.astream(sample_message):
            print("Agent response:", response)

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_routing_agent())