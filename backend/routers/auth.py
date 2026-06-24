"""
AI Personal Cloud Drive - Auth router
"""

import time
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from middleware.auth_middleware import get_client_ip
from services.auth_service import authenticate, refresh_access_token
from services.log_service import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login")
async def login(request: Request, body: LoginRequest):
    """Authenticate user and return JWT tokens."""
    ip = get_client_ip(request)
    start = time.time()

    result = authenticate(body.username, body.password, ip)

    duration_ms = int((time.time() - start) * 1000)

    if result is None:
        logger.log(
            operation="LOGIN_FAILED",
            client_ip=ip,
            status_code=401,
            duration_ms=duration_ms,
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    logger.log(
        operation="LOGIN",
        client_ip=ip,
        status_code=200,
        duration_ms=duration_ms,
    )
    return result


@router.post("/refresh")
async def refresh(request: Request, body: RefreshRequest):
    """Refresh an access token using a refresh token."""
    ip = get_client_ip(request)
    new_access_token = refresh_access_token(body.refresh_token)

    if new_access_token is None:
        logger.log(
            operation="REFRESH_FAILED",
            client_ip=ip,
            status_code=401,
        )
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return {"access_token": new_access_token, "token_type": "bearer"}
