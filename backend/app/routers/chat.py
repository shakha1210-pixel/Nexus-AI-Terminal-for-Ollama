from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.chat_service import ChatError, chat_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=20000)
    conversation_id: str | None = None
    agent_id: str = Field(default="default", min_length=1, max_length=64)
    paths: list[str] = Field(default_factory=list, max_length=10)


def _error(exc: ChatError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/conversations")
async def list_conversations() -> list[dict]:
    return chat_service.list_conversations()


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    try:
        return chat_service.get_conversation(conversation_id)
    except ChatError as exc:
        raise _error(exc) from exc


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    try:
        return chat_service.delete_conversation(conversation_id)
    except ChatError as exc:
        raise _error(exc) from exc


@router.post("/stream")
async def stream_chat(payload: ChatRequest) -> StreamingResponse:
    try:
        generator = chat_service.stream_chat(
            model=payload.model, message=payload.message,
            conversation_id=payload.conversation_id, agent_id=payload.agent_id,
            paths=payload.paths,
        )
        # Validate request and installed model before returning the stream.
        first = await generator.__anext__()
    except ChatError as exc:
        raise _error(exc) from exc

    async def events():
        yield first
        async for event in generator:
            yield event

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })
