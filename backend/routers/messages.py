"""
AI Personal Cloud Drive - Messages API Router

Cross-device chat endpoints. All require JWT authentication.
"""
import time

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, field_validator

from middleware.auth_middleware import get_current_user, get_client_ip
from services.message_service import (
    send_message,
    get_messages,
    delete_message,
    clear_messages,
)
from services.log_service import logger

router = APIRouter(prefix="/api/messages", tags=["messages"])


# ── Request models ──

class SendMessageRequest(BaseModel):
    content: str
    sender: str  # "PC" or "手机"

    @field_validator("sender")
    @classmethod
    def validate_sender(cls, v: str) -> str:
        if v not in ("PC", "手机"):
            raise ValueError("sender must be 'PC' or '手机'")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        if len(v) > 10000:
            raise ValueError("content too long (max 10000 chars)")
        return v


class MessageResponse(BaseModel):
    id: int
    content: str
    sender: str
    created_at: str


# ── Endpoints ──

@router.get("")
async def list_messages(
    request: Request,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Get recent messages (chronological order)."""
    start = time.time()
    messages = get_messages(limit=limit)
    logger.log(
        operation="MSG_LIST",
        client_ip=get_client_ip(request),
        status_code=200,
        duration_ms=int((time.time() - start) * 1000),
    )
    return {"messages": messages}


@router.post("", status_code=201)
async def post_message(
    request: Request,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    """Send a new message."""
    start = time.time()
    try:
        msg = send_message(body.content, body.sender)
        logger.log(
            operation="MSG_SEND",
            client_ip=get_client_ip(request),
            status_code=201,
            duration_ms=int((time.time() - start) * 1000),
        )
        return msg
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{msg_id}")
async def remove_message(
    msg_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Delete a single message."""
    start = time.time()
    if delete_message(msg_id):
        logger.log(
            operation="MSG_DELETE",
            client_ip=get_client_ip(request),
            status_code=200,
            duration_ms=int((time.time() - start) * 1000),
        )
        return {"detail": "deleted"}
    raise HTTPException(status_code=404, detail="Message not found")


@router.delete("")
async def clear_all_messages(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Delete all messages."""
    start = time.time()
    count = clear_messages()
    logger.log(
        operation="MSG_CLEAR",
        client_ip=get_client_ip(request),
        status_code=200,
        duration_ms=int((time.time() - start) * 1000),
    )
    return {"detail": f"Deleted {count} messages"}
