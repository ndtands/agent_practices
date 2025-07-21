import httpx
import json
import asyncio
from typing import Dict, Any
from a2a.types import (
    SendMessageRequest,
    SendMessageResponse,
    MessageSendParams,
)
from langgraph.checkpoint.memory import MemorySaver
from remote_agent_connection import RemoteAgentConnections
from a2a.client import A2ACardResolver
from langchain_core.tools import tool
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from configs import azure_gpt4o_mini

def create_send_agent_message_tool(remote_agent_connections):
    @tool
    async def send_agent_message(
        agent_name: str,
        text: str,
        config: RunnableConfig
    ) -> Dict[str, Any]:
        """Send a message to a specified agent and retrieve the response.

        Args:
            agent_name: The name of the agent to send the message to.
            message_id: The unique identifier for the message.
            text: The query text to send to the agent.

        Returns:
            A dictionary containing the agent's response or an error message if the request fails.
        """
        configurable = config.get("configurable", {})
        message_id = configurable.get("message_id", "default")
        print(f"agent_name: {agent_name} - message_id: {message_id} - text: {text}")
        try:
            payload = {
                'message': {
                    'role': 'user',
                    'parts': [
                        {'type': 'text', 'text': text}
                    ],
                    'messageId': message_id,
                },
            }
            message_request = SendMessageRequest(
                id=message_id,
                params=MessageSendParams.model_validate(payload)
            )
            client = remote_agent_connections.get(agent_name)
            if not client:
                return {'error': f'Agent {agent_name} not found.'}
            send_response: SendMessageResponse = await client.send_message(
                message_request=message_request
            )
            result = send_response.root.result
            parts = result.model_dump()['artifacts'][-1].get("parts")
            return [part.get('text') for part in parts]
        except Exception as e:
            return {'error': f'Failed to send message to agent {agent_name}: {str(e)}'}
    
    return send_agent_message

class RouterAgent:
    remote_agent_connections = {}
    
    def __init__(self, remote_agent_addresses: list[str]):
        self.remote_agent_addresses = remote_agent_addresses
        self.model = azure_gpt4o_mini
        self.agents_info = None
        self.agent_runnable = None
    
    
    async def initialize(self):
        """Initialize the async components and create the agent."""
        await self._async_init_components()
        self.agent_runnable = create_react_agent(
            model=self.model,
            tools=[create_send_agent_message_tool(self.remote_agent_connections)],
            checkpointer=MemorySaver(),
            prompt=self.get_prompt(),
        )

    async def _async_init_components(
        self
    ) -> None:
        """Asynchronous part of initialization."""
        # Use a single httpx.AsyncClient for all card resolutions for efficiency
        cards = {}
        async with httpx.AsyncClient(timeout=30) as client:
            for address in self.remote_agent_addresses:
                card_resolver = A2ACardResolver(
                    client, address
                )  # Constructor is sync
                try:
                    card = (
                        await card_resolver.get_agent_card()
                    )  # get_agent_card is async

                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    cards[card.name] = card
                except httpx.ConnectError as e:
                    print(
                        f'ERROR: Failed to get agent card from {address}: {e}'
                    )
                except Exception as e:  # Catch other potential errors
                    print(
                        f'ERROR: Failed to initialize connection for {address}: {e}'
                    )

        # Populate self.agents using the logic from original __init__ (via list_remote_agents)
        agent_info = []
        for agent_detail_dict in self.list_remote_agents(cards):
            agent_info.append(json.dumps(agent_detail_dict))
        self.agents_info = '\n'.join(agent_info)

    def get_prompt(self):
        return f"""
**Role:** You are an expert Routing Delegator. Your primary function is to accurately delegate user inquiries regarding weather or accommodations to the appropriate specialized remote agents.

**Core Directives:**

* **Task Delegation:** Utilize the `send_message` function to assign actionable tasks to remote agents.
* **Contextual Awareness for Remote Agents:** If a remote agent repeatedly requests user confirmation, assume it lacks access to the full conversation history. In such cases, enrich the task description with all necessary contextual information relevant to that         specific agent.
* **Autonomous Agent Engagement:** Never seek user permission before engaging with remote agents. If multiple agents are required to fulfill a request, connect with them directly without requesting user preference or confirmation.
* **Transparent Communication:** Always present the complete and detailed response from the remote agent to the user.
* **User Confirmation Relay:** If a remote agent asks for confirmation, and the user has not already provided it, relay this confirmation request to the user.
* **Focused Information Sharing:** Provide remote agents with only relevant contextual information. Avoid extraneous details.
* **No Redundant Confirmations:** Do not ask remote agents for confirmation of information or actions.
* **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions. If information is insufficient, request clarification from the user.
* **Prioritize Recent Interaction:** Focus primarily on the most recent parts of the conversation when processing requests.
* **Active Agent Prioritization:** If an active agent is already engaged, route subsequent related requests to that agent using the appropriate task update tool.

**Agent Roster:**

* Available Agents: `{self.agents_info}`
"""
    
    @staticmethod
    def list_remote_agents(cards):
        """List the available remote agents you can use to delegate the task."""
        if not cards:
            return []

        remote_agent_info = []
        for card in cards.values():
            print(f'Found agent card: {card.model_dump(exclude_none=True)}')
            print('=' * 100)
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info
    
