"""
AI Personal Cloud Drive - FastAPI Application Entry Point

Key design decisions for MVP public access:
- Binds to 0.0.0.0 (all IPv4) for LAN access via phone hotspot.
- Serves frontend static files directly (no Nginx required for MVP).
- Uses local CA certificates (mkcert/OpenSSL) for HTTPS on mDNS LAN.
- DDNS (Cloudflare) provides HTTPS for public domain access.

Access patterns:
  Local:  https://127.0.0.1:8000
  LAN:    https://<lan-ip>:8000
  mDNS:   https://clouddrive.local:8000
  Public: https://files.balabalashowtime.icu  (Cloudflare HTTPS proxy)
"""

import asyncio
import os
import sys
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from config import (
    DATA_DIR, HOST, PORT, FRONTEND_DIST,
    DDNS_DOMAIN, DDNS_CHECK_INTERVAL, TMP_CLEANUP_INTERVAL,
    ADMIN_USERNAME, ADMIN_PASSWORD,
    SSL_ENABLED, SSL_KEYFILE, SSL_CERTFILE,
)
from models.database import init_db
from routers.auth import router as auth_router
from routers.files import router as files_router
from routers.ddns import router as ddns_router
from services.ddns_service import ddns_check_loop, get_public_ipv6, get_ddns_status
from services.file_service import cleanup_tmp_files
from services.mdns_service import start_mdns, stop_mdns, get_status as get_mdns_status


async def tmp_cleanup_loop():
    """Background task: periodically clean up stale .tmp files."""
    while True:
        try:
            cleanup_tmp_files()
        except Exception as e:
            print(f"[Cleanup] Error: {e}")
        await asyncio.sleep(TMP_CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # ---- Startup ----
    print()
    print("=" * 60)
    print("  [Server] AI Personal Cloud Drive - Starting Up")
    print("=" * 60)

    # Init database
    init_db(ADMIN_USERNAME, ADMIN_PASSWORD)

    # Detect IPv6
    print(f"  [Network] Detecting public IPv6 address...")
    ipv6 = get_public_ipv6()
    if ipv6:
        print(f"           Public IPv6: {ipv6}")
    else:
        print(f"           No public IPv6 — is phone hotspot connected?")

    # Start mDNS for LAN access
    protocol = "https" if SSL_ENABLED else "http"
    print(f"  [mDNS]    Registering clouddrive.local ({protocol}) on LAN...")
    lan_ip = start_mdns(PORT, protocol=protocol)
    print()

    # Print access URLs
    print(f"  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │  Local:          {protocol}://127.0.0.1:{PORT}                 │")
    if lan_ip:
        print(f"  │  LAN (mDNS):     {protocol}://clouddrive.local:{PORT}          │")
        print(f"  │  LAN (direct):   {protocol}://{lan_ip}:{PORT}                  │")
    if ipv6:
        print(f"  │  Public (IPv6):  {protocol}://[{ipv6}]:{PORT}                  │")
    if DDNS_DOMAIN:
        print(f"  │  Public (domain): https://{DDNS_DOMAIN}                       │")
    print(f"  │                                                         │")
    print(f"  │  API Docs:        {protocol}://127.0.0.1:{PORT}/docs           │")
    print(f"  │  Default login:   {ADMIN_USERNAME} / {ADMIN_PASSWORD}    │")
    if SSL_ENABLED:
        print(f"  │  SSL:             Local CA — install rootCA.pem on phone│")
    print(f"  └─────────────────────────────────────────────────────────┘")
    print()

    # Check frontend
    if FRONTEND_DIST.is_dir():
        print(f"  [OK] Frontend found — serving static files")
    else:
        print(f"  [!!] Frontend not built — run: cd frontend && npm run build")

    print()

    # Start background tasks
    ddns_task = asyncio.create_task(ddns_check_loop())
    cleanup_task = asyncio.create_task(tmp_cleanup_loop())

    yield

    # ---- Shutdown ----
    ddns_task.cancel()
    cleanup_task.cancel()
    stop_mdns()
    try:
        await asyncio.gather(ddns_task, cleanup_task)
    except asyncio.CancelledError:
        pass
    print("[Server] Shutdown complete")


app = FastAPI(
    title="AI Personal Cloud Drive",
    version="1.0.0-mvp",
    lifespan=lifespan,
)

# CORS - allow public access from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- API Routers ----
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(ddns_router)


@app.get("/api/health")
async def health():
    """Public health check — no auth required."""
    ipv6 = get_public_ipv6()
    protocol = "https" if SSL_ENABLED else "http"
    return {
        "status": "ok",
        "version": "1.0.0-mvp",
        "ssl_enabled": SSL_ENABLED,
        "public_ipv6": ipv6,
        "domain": DDNS_DOMAIN,
        "accessible_at": f"{protocol}://{DDNS_DOMAIN}:{PORT}" if ipv6 else None,
    }


@app.get("/api/public-status")
async def public_status():
    """
    Public status endpoint — no auth required.
    Use this to verify the server is reachable from the internet.
    """
    ddns = get_ddns_status()
    mdns = get_mdns_status()
    return {
        "server": "running",
        "bind_host": HOST,
        "bind_port": PORT,
        "ssl_enabled": SSL_ENABLED,
        "protocol": "https" if SSL_ENABLED else "http",
        "public_ipv6": ddns.get("ipv6"),
        "domain": DDNS_DOMAIN,
        "ddns": ddns,
        "mdns": mdns,
        "frontend_available": FRONTEND_DIST.is_dir(),
    }


# ---- Serve Frontend (for MVP — no Nginx required) ----
if FRONTEND_DIST.is_dir():
    # Mount static assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """
        SPA fallback: serve index.html for all non-API routes.
        This allows React Router to handle client-side routing.
        """
        # If it's an API path, let FastAPI handle it (404 from API routers)
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not found"}, status_code=404)

        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))

        # SPA fallback: serve index.html for all other paths
        index_path = FRONTEND_DIST / "index.html"
        if index_path.is_file():
            return FileResponse(str(index_path))

        return JSONResponse({"detail": "Frontend not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    print("Starting AI Personal Cloud Drive...")
    print(f"Host: {HOST}  Port: {PORT}")
    print(f"SSL: {'enabled' if SSL_ENABLED else 'disabled'}")
    print(f"Frontend: {'available' if FRONTEND_DIST.is_dir() else 'NOT BUILT'}")

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,
        server_header=False,
        ssl_keyfile=str(SSL_KEYFILE) if SSL_ENABLED else None,
        ssl_certfile=str(SSL_CERTFILE) if SSL_ENABLED else None,
    )
