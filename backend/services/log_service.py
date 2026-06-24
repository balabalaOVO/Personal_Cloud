"""
AI Personal Cloud Drive - Logging service

Provides structured logging with daily rotation and auto-cleanup.
"""

import logging
import logging.handlers
import os
import re
import time
from pathlib import Path
from config import LOGS_DIR, LOG_RETENTION_DAYS


class CloudDriveLogger:
    """
    Custom logger that writes operation logs in the standard format:
    [timestamp] [client_ip] [operation] [file_path] [status_code] [file_size] [duration_ms]
    """

    def __init__(self):
        self._logger = logging.getLogger("clouddrive")
        self._logger.setLevel(logging.INFO)

        # Daily rotation at midnight
        handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(LOGS_DIR / "cloud-drive.log"),
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
        handler.suffix = "%Y-%m-%d"

        # Custom formatter
        handler.setFormatter(logging.Formatter(
            "%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        self._logger.addHandler(handler)

        # Also log to console in development
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(console)

    def _format_size(self, size_bytes: int | None) -> str:
        if size_bytes is None:
            return "-"
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    def log(
        self,
        operation: str,
        client_ip: str = "-",
        file_path: str = "-",
        status_code: int = 0,
        file_size: int | None = None,
        duration_ms: int = 0,
    ):
        """Write an operation log entry."""
        msg = (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"[{client_ip}] "
            f"[{operation}] "
            f"[{file_path}] "
            f"[{status_code}] "
            f"[{self._format_size(file_size)}] "
            f"[{duration_ms}ms]"
        )
        self._logger.info(msg)

    def cleanup_old_logs(self):
        """Remove log files older than LOG_RETENTION_DAYS."""
        cutoff = time.time() - LOG_RETENTION_DAYS * 24 * 3600
        pattern = re.compile(r"cloud-drive\.log\.(\d{4}-\d{2}-\d{2})")
        for f in LOGS_DIR.iterdir():
            match = pattern.match(f.name)
            if match:
                try:
                    if f.stat().st_mtime < cutoff:
                        f.unlink()
                except OSError:
                    pass


# Singleton
logger = CloudDriveLogger()
