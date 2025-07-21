from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
from agent import AirbnbAgent

async def get_tools():
    SERVER_CONFIGS = {
        'bnb': {
            'command': 'npx',
            'args': ['-y', '@openbnb/mcp-server-airbnb', '--ignore-robots-txt'],
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
    agent = AirbnbAgent(mcp_tools=tools)
    response = await agent.ainvoke(
        query="Please find a room in LA, CA, June 20-25, 2025, two adults",
        session_id="session_123"
    )
    print(response)



if __name__ == "__main__":
    asyncio.run(main())