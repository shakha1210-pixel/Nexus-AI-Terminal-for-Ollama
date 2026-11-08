from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal

from app.services.agent_access_service import AgentAccessError, agent_access_service
from app.services.agent_runtime_service import AgentRuntimeError, agent_runtime_service
from app.services.agent_control_service import AgentControlError, agent_control_service

router = APIRouter(prefix="/api/agents", tags=["Agent Access"])


class ReadGrant(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class ContextRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=10)


class AgentRunRequest(BaseModel):
    model: str = Field(min_length=1, max_length=160)
    task: str = Field(min_length=1, max_length=12000)


class AgentModeRequest(BaseModel):
    mode: Literal["read_only", "approval_required", "autopilot", "locked"]


class IsolationRequest(BaseModel):
    reason: str = Field(default="Manual isolation", max_length=500)


def _error(exc: AgentAccessError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/{agent_id}/permissions")
async def get_permissions(agent_id: str) -> dict:
    try:
        return agent_access_service.list_permissions(agent_id)
    except AgentAccessError as exc:
        raise _error(exc) from exc


@router.post("/{agent_id}/permissions/read")
async def grant_read(agent_id: str, payload: ReadGrant) -> dict:
    try:
        return agent_access_service.grant_read(agent_id, payload.path)
    except AgentAccessError as exc:
        raise _error(exc) from exc


@router.delete("/{agent_id}/permissions/read")
async def revoke_read(agent_id: str, path: str) -> dict:
    try:
        return agent_access_service.revoke_read(agent_id, path)
    except AgentAccessError as exc:
        raise _error(exc) from exc


@router.post("/{agent_id}/context")
async def prepare_context(agent_id: str, payload: ContextRequest) -> dict:
    try:
        return agent_access_service.build_context(agent_id, payload.paths)
    except AgentAccessError as exc:
        raise _error(exc) from exc

@router.post("/{agent_id}/run")
async def run_agent(agent_id: str, payload: AgentRunRequest) -> StreamingResponse:
    try:
        generator = agent_runtime_service.run(agent_id=agent_id, model=payload.model, task=payload.task)
        first = await generator.__anext__()
    except AgentRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def events():
        yield first
        try:
            async for event in generator:
                yield event
        except AgentRuntimeError as exc:
            import json
            yield "event: error\ndata: " + json.dumps({"message": str(exc)}, ensure_ascii=False) + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })

 
@router.get("/{agent_id}/control")
async def get_agent_control(agent_id: str) -> dict:
    try:
        return agent_control_service.get(agent_id)
    except AgentControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{agent_id}/control/mode")
async def set_agent_mode(agent_id: str, payload: AgentModeRequest) -> dict:
    try:
        return agent_control_service.set_mode(agent_id, payload.mode)
    except AgentControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{agent_id}/isolate")
async def isolate_agent(agent_id: str, payload: IsolationRequest) -> dict:
    try:
        return agent_control_service.isolate(agent_id, payload.reason)
    except AgentControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{agent_id}/release")
async def release_agent(agent_id: str) -> dict:
    try:
        return agent_control_service.release(agent_id)
    except AgentControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
