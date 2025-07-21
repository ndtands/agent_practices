import asyncio
import traceback
from collections.abc import AsyncIterator
from pprint import pformat
from uuid import uuid4
import gradio as gr
from routing_agent import RouterAgent
from langchain_core.messages import AIMessageChunk

# Configuration for remote agent addresses
remote_agent_addresses = [
    'http://localhost:10002',
    'http://localhost:10001'
]

APP_NAME = 'routing_app'
USER_ID = 'default_user'
SESSION_ID = 'default_session'

# Initialize the RouterAgent
async def initialize_agent(remote_agent_addresses):
    """Initialize the RouterAgent."""
    print('Initializing RouterAgent...')
    agent = RouterAgent(remote_agent_addresses)
    await agent.initialize()  # Call the async initialization
    print('RouterAgent initialized successfully.')
    return agent.agent_runnable

# Global agent runnable (initialized once)
agent_runnable = asyncio.run(initialize_agent(remote_agent_addresses))

async def get_response_from_agent(
    message: str,
    history: list[gr.ChatMessage],
) -> AsyncIterator[gr.ChatMessage]:
    """Get response from the RouterAgent."""
    try:
        # Prepare the input for langgraph
        langgraph_input = {'messages': [('user', message)]}
        config = {'configurable': {'thread_id': SESSION_ID, 'message_id': uuid4().hex}}

        # Stream events from the agent
        content = ""
        tool_content = ""
        async for event in agent_runnable.astream_events(langgraph_input, config, version='v1'):
            data = event['data']
            if data.get('chunk'):
                chunk = data.get('chunk')
                if isinstance(chunk, AIMessageChunk):
                    additional_kwargs = chunk.additional_kwargs
                    if additional_kwargs:
                        tool_call = additional_kwargs.get('tool_calls')[-1]
                        id = tool_call.get('id')
                        function = tool_call.get('function')
                        if id:
                            function_name = function.get("name")
                            tool_content+=f'\n\n🛠️ **Tool Call: {function_name}**\n'
                        else:
                            arguments =function.get("arguments")
                            tool_content+=f"{arguments}"
                        yield gr.ChatMessage(
                            role='assistant',
                            content=tool_content,
                        )
                    else:
                        content +=chunk.content
                        yield gr.ChatMessage(
                            role='assistant',
                            content=content
                        )
    except Exception as e:
        print(f'Error in get_response_from_agent (Type: {type(e)}): {e}')
        traceback.print_exc()  # Print the full traceback
        yield gr.ChatMessage(
            role='assistant',
            content='An error occurred while processing your request. Please check the server logs for details.',
        )

async def main():
    """Main Gradio app."""
    with gr.Blocks(
        theme=gr.themes.Ocean(), title='A2A Host Agent with Logo'
    ) as demo:
        gr.Image(
            'static/a2a.png',
            width=100,
            height=100,
            scale=0,
            show_label=False,
            show_download_button=False,
            container=False,
            show_fullscreen_button=False,
        )
        gr.ChatInterface(
            get_response_from_agent,
            title='A2A Host Agent',
            description='This assistant can help you to check weather and find Airbnb accommodation',
        )

    print('Launching Gradio interface...')
    demo.queue().launch(
        server_name='0.0.0.0',
        server_port=8083,
    )
    print('Gradio application has been shut down.')

if __name__ == '__main__':
    asyncio.run(main())