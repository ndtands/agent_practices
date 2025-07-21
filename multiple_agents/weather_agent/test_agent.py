from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
from agent import WeatherAgent

async def get_tools():
    SERVER_CONFIGS = {
        'weather': {
            'command': 'python',
            'args': ['./weather_mcp.py'],
            'transport': 'stdio',
        },
    }
    mcp_client_instance = MultiServerMCPClient(SERVER_CONFIGS)
    mcp_tools = await mcp_client_instance.get_tools()
    return mcp_tools

async def main():
    # Khởi tạo agent
    tools = await get_tools()
    print(f"tools: {tools}")
    agent = WeatherAgent(mcp_tools=tools)
    response = await agent.ainvoke(
        query="What's the weather like in San Francisco?",
        session_id="session_123"
    )
    print(response)

async def main_with_stream():
    # Khởi tạo agent
    tools = await get_tools()
    
    agent = WeatherAgent(mcp_tools=tools)
    async for chunk in agent.astream(
        query="What's the weather like in San Francisco?",
        session_id="session_123"
    ):
        print(chunk)


if __name__ == "__main__":
    asyncio.run(main())