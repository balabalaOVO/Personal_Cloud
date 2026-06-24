"""
AI Personal Cloud Drive - DDNS status router
"""

from fastapi import APIRouter, Depends
from middleware.auth_middleware import get_current_user
from services.ddns_service import get_ddns_status

router = APIRouter(prefix="/api/ddns", tags=["ddns"])


@router.get("/status")
async def ddns_status(user: dict = Depends(get_current_user)):
    """Get DDNS status (current IPv6, last check, last update)."""
    return get_ddns_status()
