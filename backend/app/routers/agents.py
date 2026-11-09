import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal

from app.services.agent_access_service import AgentAccessError, agent_access_service
from app.services.agent_runtime_service import AgentRuntimeError, agent_runtime_service
from app.services.agent_control_service import AgentControlError, agent_control_service
from app.services.agent_approval_service import AgentApprovalError, agent_approval_service

router = APIRouter(prefix="/api/agents", tags=["Agent Access"])


class ReadGrant(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class ContextRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=10)


class AgentRunRequest(BaseModel):
    model: str = Field(min_length=1, max_length=160)
    provider_id: str | None = Field(default=None, max_length=80)
    task: str = Field(min_length=1, max_length=12000)


class AgentModeRequest(BaseModel):
    mode: Literal["read_only", "approval_required", "autopilot", "locked"]


class IsolationRequest(BaseModel):
    reason: str = Field(default="Manual isolation", max_length=500)


class ApprovalDecision(BaseModel):
    approve: bool


def _error(exc: AgentAccessError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("")
async def list_agents() -> dict:
    return {"agent_ids": sorted(set(agent_control_service.list_agent_ids()) | set(agent_access_service.list_agent_ids()))}


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
        generator = agent_runtime_service.run(agent_id=agent_id, model=payload.model, task=payload.task, provider_id=payload.provider_id)
        first = await generator.__anext__()
    except AgentRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Agent ishga tushmadi. Kutilmagan server xatoligi yuz berdi.") from exc

    async def events():
        yield first
        try:
            async for event in generator:
                yield event
        except AgentRuntimeError as exc:
            yield "event: error\\ndata: " + json.dumps({"message": str(exc)}, ensure_ascii=False) + "\\n\\n"
        except Exception:
            yield "event: error\\ndata: " + json.dumps(
                {"message": "Agent oqimida kutilmagan xatolik yuz berdi."}, ensure_ascii=False
            ) + "\\n\\n"

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


@router.get("/{agent_id}/approvals")
async def list_agent_approvals(agent_id: str, pending_only: bool = True) -> dict:
    try:
        return agent_approval_service.list_requests(agent_id, pending_only=pending_only)
    except AgentApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{agent_id}/approvals/{request_id}/decision")
async def decide_agent_approval(agent_id: str, request_id: str, payload: ApprovalDecision) -> dict:
    try:
        return agent_approval_service.decide(agent_id, request_id, payload.approve)
    except AgentApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
