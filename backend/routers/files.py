"""
AI Personal Cloud Drive - File management router
"""

import os
import time
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import FileResponse

from middleware.auth_middleware import get_current_user, get_client_ip
from services.auth_service import verify_token, _create_access_token
from services.file_service import (
    list_files,
    upload_file,
    download_file,
    mkdir,
    rename,
    delete,
    is_blocked_extension,
    BLOCKED_EXTENSIONS,
)
from services.log_service import logger
from config import JWT_SECRET, JWT_ALGORITHM

router = APIRouter(prefix="/api/files", tags=["files"])


# ── Helper: download token ──────────────────────────────────────────

def _verify_download_token(token: str, expected_path: str) -> bool:
    """Verify a short-lived download token is valid for the given file path."""
    import jwt
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "download":
            return False
        if payload.get("path") != expected_path:
            return False
        return True
    except Exception:
        return False


def _get_user_from_request(request: Request, file_path: str) -> dict | None:
    """
    Authenticate via Authorization header OR download token query param.
    Returns user payload dict or None.
    """
    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload:
            return payload

    # Try download token in query param
    token = request.query_params.get("token")
    if token and _verify_download_token(token, file_path):
        return {"sub": "download-token", "username": "download"}

    return None


# ── Routes ───────────────────────────────────────────────────────────

@router.get("")
async def get_files(
    request: Request,
    path: str = Query(default="/", description="Directory path"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=500),
    sort: str = Query(default="name", pattern="^(name|size|time)$"),
    user: dict = Depends(get_current_user),
):
    """List files and directories."""
    ip = get_client_ip(request)
    start = time.time()

    try:
        result = list_files(relative_path=path, page=page, size=size, sort=sort)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    duration_ms = int((time.time() - start) * 1000)
    logger.log(operation="LIST", client_ip=ip, file_path=path,
               status_code=200, duration_ms=duration_ms)

    return result


@router.post("/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    path: str = Form(default="/"),
    sha256: str = Form(default=""),
    user: dict = Depends(get_current_user),
):
    """Upload a file."""
    ip = get_client_ip(request)
    start = time.time()

    if is_blocked_extension(file.filename):
        logger.log(operation="UPLOAD_BLOCKED", client_ip=ip,
                   file_path=f"{path}/{file.filename}",
                   status_code=403, duration_ms=0)
        raise HTTPException(status_code=403,
                            detail=f"File type blocked for security reasons")

    try:
        content = await file.read()
        result = upload_file(
            file_content=content,
            filename=file.filename,
            relative_path=path,
            expected_sha256=sha256 if sha256 else None,
        )

        duration_ms = int((time.time() - start) * 1000)

        if not result["success"]:
            raise HTTPException(status_code=403, detail=result["error"])

        logger.log(operation="UPLOAD", client_ip=ip,
                   file_path=f"{path}/{file.filename}",
                   status_code=200, file_size=len(content),
                   duration_ms=duration_ms)

        return result

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.log(operation="UPLOAD", client_ip=ip,
                   file_path=f"{path}/{file.filename}",
                   status_code=500, duration_ms=duration_ms)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-token")
async def create_download_token(
    request: Request,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """
    Create a short-lived download token for a specific file.
    This allows direct browser download without the fetch+blob approach.
    Token is valid for 30 seconds and scoped to a single file path.
    """
    import jwt
    file_path = body.get("path", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="path is required")

    now = int(time.time())
    payload = {
        "sub": user["sub"],
        "username": user["username"],
        "type": "download",
        "path": file_path,
        "iat": now,
        "exp": now + 60,  # 60 seconds — enough to start the download on mobile
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"token": token, "expires_in": 30}


@router.get("/download")
async def download(
    request: Request,
    path: str = Query(..., description="File path to download"),
):
    """
    Download a file.

    Auth via:
      - Authorization: Bearer <token> header (standard)
      - ?token=<download_token> query param (for direct browser download)
    """
    ip = get_client_ip(request)

    # Authenticate
    user = _get_user_from_request(request, path)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    start = time.time()

    try:
        file_path_obj, filename = download_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    file_size = file_path_obj.stat().st_size

    duration_ms = int((time.time() - start) * 1000)
    logger.log(operation="DOWNLOAD", client_ip=ip, file_path=path,
               status_code=200, file_size=file_size, duration_ms=duration_ms)

    # Use inline Content-Disposition so the browser downloads directly
    from urllib.parse import quote
    encoded_filename = quote(filename, safe='')
    return FileResponse(
        path=str(file_path_obj),
        filename=filename,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
    )


@router.post("/mkdir")
async def create_dir(
    request: Request,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Create a new directory."""
    ip = get_client_ip(request)
    start = time.time()

    relative_path = body.get("path", "/")
    name = body.get("name", "")

    try:
        result = mkdir(relative_path, name)
    except (FileExistsError, ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    duration_ms = int((time.time() - start) * 1000)
    logger.log(operation="MKDIR", client_ip=ip,
               file_path=f"{relative_path}/{name}",
               status_code=200, duration_ms=duration_ms)

    return result


@router.put("/rename")
async def rename_file(
    request: Request,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Rename a file or directory."""
    ip = get_client_ip(request)
    start = time.time()

    relative_path = body.get("path", "")
    new_name = body.get("new_name", "")

    try:
        result = rename(relative_path, new_name)
    except (FileExistsError, FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    duration_ms = int((time.time() - start) * 1000)
    logger.log(operation="RENAME", client_ip=ip, file_path=relative_path,
               status_code=200, duration_ms=duration_ms)

    return result


@router.delete("")
async def delete_file(
    request: Request,
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Delete a file or directory (soft delete to trash)."""
    ip = get_client_ip(request)
    start = time.time()

    relative_path = body.get("path", "")

    try:
        result = delete(relative_path)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    duration_ms = int((time.time() - start) * 1000)
    logger.log(operation="DELETE", client_ip=ip, file_path=relative_path,
               status_code=200, duration_ms=duration_ms)

    return result
