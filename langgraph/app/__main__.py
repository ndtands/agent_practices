import logging
import os
import sys

import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.tasks import InMemoryPushNotificationConfigStore, BasePushNotificationSender
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from app.agent_executor import CurrencyAgentExecutor
from app.agent import CurrencyAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    try:
        capabilities = AgentCapabilities(
            streaming=True,
            pushNotifications=True
        )
        skill = AgentSkill(
            id="convert_currency",
            name="Currency Exchange Rates Tool",
            description='Helps with exchange values between various currencies',
            tags=['currency conversion', 'currency exchange'],
            examples=['What is exchange rate between USD and GBP?'],
        )
        agent_card = AgentCard(
            name='Currency Agent',
            description='Helps with exchange rates for currencies',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        httpx_client = httpx.AsyncClient()
        push_notification_config_store = InMemoryPushNotificationConfigStore()
        push_notification_sender = BasePushNotificationSender(
            httpx_client,
            config_store=push_notification_config_store
        )
        request_handler = DefaultRequestHandler(
            agent_executor=CurrencyAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_sender=push_notification_sender,
        )

        server = A2AStarletteApplication(
                agent_card=agent_card, http_handler=request_handler
            )
        
        uvicorn.run(server.build(), host=host, port=port)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()

# Fixbug cannot run `uv run app` directly
# cd /Users/nguyenduytan/Desktop/learning/mcp_code/langgraph
# uv pip install -e .

