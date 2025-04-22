"""API routes for the block-based agentic pipeline system."""

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from block_agents.core.config import Config
from block_agents.core.errors import BlockAgentError
from block_agents.core.pipeline import Pipeline

router = APIRouter()

# Models for request and response
class PipelineInput(BaseModel):
    """Input for a pipeline execution request."""
    
    pipeline_id: str = Field(..., description="Unique identifier for the pipeline")
    input_values: Dict[str, Any] = Field(
        default_factory=dict, description="Input values for the pipeline blocks"
    )


class PipelineExecuteResponse(BaseModel):
    """Response for a pipeline execution request."""
    
    execution_id: str = Field(..., description="Unique identifier for the execution")
    status: str = Field(..., description="Execution status")
    message: str = Field(None, description="Additional message")


class PipelineStatusResponse(BaseModel):
    """Response for a pipeline status request."""
    
    execution_id: str = Field(..., description="Unique identifier for the execution")
    status: str = Field(..., description="Execution status")
    pipeline_id: str = Field(..., description="Pipeline identifier")
    progress: float = Field(..., description="Execution progress (0-1)")
    completed_blocks: List[str] = Field(
        default_factory=list, description="List of completed block IDs"
    )
    pending_blocks: List[str] = Field(
        default_factory=list, description="List of pending block IDs"
    )
    result: Optional[Dict[str, Any]] = Field(
        None, description="Execution result (if completed)"
    )


# In-memory store for execution state
executions = {}


@router.post("/pipelines/execute", response_model=PipelineExecuteResponse)
async def execute_pipeline(pipeline_input: PipelineInput = Body(...)):
    """Execute a pipeline with the given input values.

    Args:
        pipeline_input: Pipeline execution request

    Returns:
        Execution response
    """
    try:
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Store execution
        executions[execution_id] = {
            "status": "pending",
            "pipeline_id": pipeline_input.pipeline_id,
            "input_values": pipeline_input.input_values,
            "progress": 0.0,
            "completed_blocks": [],
            "pending_blocks": [],
            "result": None,
        }
        
        # Start pipeline execution asynchronously
        # For now, just update the status as if it completed instantly
        # In a real implementation, this would start a background task
        executions[execution_id]["status"] = "completed"
        executions[execution_id]["progress"] = 1.0
        executions[execution_id]["result"] = {"message": "Pipeline executed successfully"}
        
        return PipelineExecuteResponse(
            execution_id=execution_id,
            status="pending",
            message="Pipeline execution started",
        )
        
    except BlockAgentError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines/{execution_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(execution_id: str):
    """Get the status of a pipeline execution.

    Args:
        execution_id: Execution ID

    Returns:
        Execution status
    """
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
        
    execution = executions[execution_id]
    
    return PipelineStatusResponse(
        execution_id=execution_id,
        status=execution["status"],
        pipeline_id=execution["pipeline_id"],
        progress=execution["progress"],
        completed_blocks=execution["completed_blocks"],
        pending_blocks=execution["pending_blocks"],
        result=execution["result"],
    )


@router.get("/pipelines/{execution_id}/result")
async def get_pipeline_result(execution_id: str):
    """Get the result of a pipeline execution.

    Args:
        execution_id: Execution ID

    Returns:
        Execution result
    """
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
        
    execution = executions[execution_id]
    
    if execution["status"] != "completed":
        raise HTTPException(status_code=400, detail="Pipeline execution not completed")
        
    return JSONResponse(content=execution["result"])


@router.delete("/pipelines/{execution_id}")
async def cancel_pipeline(execution_id: str):
    """Cancel a pipeline execution.

    Args:
        execution_id: Execution ID

    Returns:
        Success message
    """
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
        
    # Update status
    executions[execution_id]["status"] = "cancelled"
    
    return {"message": "Pipeline execution cancelled"}


@router.get("/pipelines")
async def list_pipelines():
    """List all pipeline executions.

    Returns:
        List of executions
    """
    return {
        execution_id: {
            "status": execution["status"],
            "pipeline_id": execution["pipeline_id"],
            "progress": execution["progress"],
        }
        for execution_id, execution in executions.items()
    }