"""
AI Personal Cloud Drive - Configuration

Loads from .env file first (if exists), then environment variables.
"""

import os
from pathlib import Path

# ---- Load .env file ----
try:
    from dotenv import load_dotenv
    _env_file = Path(os.path.dirname(os.path.abspath(__file__))) / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv not required for production

# ---- Paths ----
BACKEND_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = BACKEND_DIR.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CERT_DIR = BASE_DIR / "certs"
DB_PATH = DATA_DIR / "clouddrive.db"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# ---- Server ----
# IMPORTANT: Must listen on all interfaces for LAN access.
# On Windows, Python binds "::" as IPv6-only (not dual-stack), so IPv4 fails.
# Use "0.0.0.0" for IPv4 LAN access. Add Nginx dual-stack proxy later for IPv6.
HOST = os.getenv("CLOUD_DRIVE_HOST", "0.0.0.0")
PORT = int(os.getenv("CLOUD_DRIVE_PORT", "8000"))
# Base URL for external access (used in startup messages and status)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

# ---- SSL / HTTPS (mkcert local CA for mDNS) ----
SSL_KEYFILE = CERT_DIR / "server.key"
SSL_CERTFILE = CERT_DIR / "server.crt"
# True if both cert files exist → serve HTTPS
SSL_ENABLED = SSL_KEYFILE.is_file() and SSL_CERTFILE.is_file()

# ---- Auth ----
JWT_SECRET = os.getenv("CLOUD_DRIVE_JWT_SECRET", "CHANGE-ME-TO-A-RANDOM-SECRET-AT-LEAST-32-CHARS")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120      # 2 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7
LOGIN_MAX_ATTEMPTS = 5                 # max failed attempts per minute per IP
LOGIN_LOCKOUT_WINDOW = 60              # seconds

# ---- Initial Admin User ----
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ---- Files ----
BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".sys", ".bat", ".cmd", ".ps1", ".sh",
    ".bash", ".zsh", ".run", ".bin", ".com", ".msi", ".scr",
    ".vbs", ".wsf", ".jar", ".pyc", ".pyo"
}
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB
TMP_CLEANUP_INTERVAL = 30 * 60           # 30 minutes (seconds)
TRASH_DIR_NAME = ".trash"

# ---- DDNS ----
DDNS_CHECK_INTERVAL = int(os.getenv("DDNS_CHECK_INTERVAL", "60"))   # seconds
DDNS_DOMAIN = os.getenv("DDNS_DOMAIN", "files.balabalashowtime.icu")
DDNS_TTL = int(os.getenv("DDNS_TTL", "600"))                        # DNS TTL in seconds
# Cloudflare API credentials
#  - API Token: create at https://dash.cloudflare.com/profile/api-tokens
#    Needs permissions: Zone → DNS → Edit
#  - Zone ID:   found on your domain's overview page in Cloudflare dashboard
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")

# ---- Logging ----
LOG_RETENTION_DAYS = 30
LOG_FORMAT = "[%(asctime)s] [%(client_ip)s] [%(operation)s] [%(file_path)s] [%(status_code)s] [%(file_size)s] [%(duration_ms)s]"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
