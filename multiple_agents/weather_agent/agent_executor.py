import logging
from typing import Any, override
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
    new_text_artifact,
)
from agent import WeatherAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherAgentExecutor(AgentExecutor):
    """WeatherAgentExecutor Example."""
    def __init__(self, mcp_tools: list[Any]):
        """Initializes the WeatherAgentExecutor.

        Args:
            mcp_tools: A list of preloaded MCP tools for the AirbnbAgent.
        """
        super().__init__()
        logger.info(
            f'Initializing WeatherAgentExecutor with {len(mcp_tools) if mcp_tools else "no"} MCP tools.'
        )
        self.agent = WeatherAgent(mcp_tools=mcp_tools)

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        task = context.current_task

        if not context.message:
            raise Exception('No message provided')
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        
        # invoke the underlying agent, using streaming results
        async for event in self.agent.astream(query, task.contextId):
            if event['is_task_complete']:
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=False,
                        contextId=task.contextId,
                        taskId=task.id,
                        lastChunk=True,
                        artifact=new_text_artifact(
                            name='current_result',
                            description='Result of request to agent.',
                            text=event['content'],
                        ),
                    )
                )
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(state=TaskState.completed),
                        final=True,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )
            elif event['require_user_input']:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.input_required,
                            message=new_agent_text_message(
                                event['content'],
                                task.contextId,
                                task.id,
                            ),
                        ),
                        final=True,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )
            else:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.working,
                            message=new_agent_text_message(
                                event['content'],
                                task.contextId,
                                task.id,
                            ),
                        ),
                        final=False,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')
