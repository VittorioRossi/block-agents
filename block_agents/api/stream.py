"""Streaming API endpoints for the block-based agentic pipeline system."""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Set

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from block_agents.core.errors import BlockAgentError
from block_agents.core.stream import StreamEvent

router = APIRouter()

# Dictionary mapping execution IDs to sets of streaming connections
connections: Dict[str, Set[asyncio.Queue]] = {}


class StreamManager:
    """Manages streaming connections for pipeline executions."""

    @staticmethod
    async def add_connection(execution_id: str, queue: asyncio.Queue) -> None:
        """Add a streaming connection for a pipeline execution.

        Args:
            execution_id: Execution ID
            queue: Queue for sending events
        """
        if execution_id not in connections:
            connections[execution_id] = set()
        connections[execution_id].add(queue)

    @staticmethod
    async def remove_connection(execution_id: str, queue: asyncio.Queue) -> None:
        """Remove a streaming connection for a pipeline execution.

        Args:
            execution_id: Execution ID
            queue: Queue for sending events
        """
        if execution_id in connections and queue in connections[execution_id]:
            connections[execution_id].remove(queue)
            if not connections[execution_id]:
                del connections[execution_id]

    @staticmethod
    async def broadcast_event(execution_id: str, event: StreamEvent) -> None:
        """Broadcast an event to all streaming connections for a pipeline execution.

        Args:
            execution_id: Execution ID
            event: Event to broadcast
        """
        if execution_id in connections:
            for queue in connections[execution_id]:
                await queue.put(event)


@router.get("/pipelines/{execution_id}/stream")
async def stream_pipeline_events(request: Request, execution_id: str = Path(...)):
    """Stream events for a pipeline execution.

    Args:
        request: Request object
        execution_id: Execution ID

    Returns:
        Server-sent events stream
    """
    async def event_generator():
        # Create queue for events
        queue = asyncio.Queue()
        
        # Add connection
        await StreamManager.add_connection(execution_id, queue)
        
        try:
            # Send initial event
            initial_event = StreamEvent(
                event_type="connection_established",
                pipeline_id="",
                block_id="",
                data={"execution_id": execution_id},
            )
            yield initial_event.to_sse()
            
            # Stream events
            while True:
                try:
                    # Get next event (with timeout)
                    event = await asyncio.wait_for(queue.get(), timeout=60)
                    
                    # Send event
                    yield event.to_sse()
                    
                    # Mark task as done
                    queue.task_done()
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat_event = StreamEvent(
                        event_type="heartbeat",
                        pipeline_id="",
                        block_id="",
                        data={},
                    )
                    yield heartbeat_event.to_sse()
                
        except asyncio.CancelledError:
            # Remove connection
            await StreamManager.remove_connection(execution_id, queue)
            
        # Return function
        return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.websocket("/ws/pipelines/{execution_id}")
async def websocket_pipeline_events(websocket: WebSocket, execution_id: str = Path(...)):
    """WebSocket endpoint for streaming pipeline events.

    Args:
        websocket: WebSocket connection
        execution_id: Execution ID
    """
    await websocket.accept()
    
    # Create queue for events
    queue = asyncio.Queue()
    
    # Add connection
    await StreamManager.add_connection(execution_id, queue)
    
    try:
        # Send initial event
        initial_event = StreamEvent(
            event_type="connection_established",
            pipeline_id="",
            block_id="",
            data={"execution_id": execution_id},
        )
        await websocket.send_json(initial_event.to_dict())
        
        # Stream events
        while True:
            # Start a task to wait for the next event
            event_task = asyncio.create_task(queue.get())
            
            # Start a task to receive messages from the WebSocket
            recv_task = asyncio.create_task(websocket.receive_text())
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [event_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                
            # Process completed tasks
            for task in done:
                if task is event_task:
                    # Got an event, send it to the WebSocket
                    event = task.result()
                    await websocket.send_json(event.to_dict())
                    queue.task_done()
                else:
                    # Got a message from the WebSocket
                    # Currently, we don't do anything with these messages
                    pass
                    
    except WebSocketDisconnect:
        # WebSocket disconnected
        pass
    finally:
        # Remove connection
        await StreamManager.remove_connection(execution_id, queue)
        
        # Close WebSocket if it's still open
        try:
            await websocket.close()
        except:
            pass