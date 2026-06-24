"""
AI Personal Cloud Drive - File operation service
"""

import os
import hashlib
import shutil
import time
from pathlib import Path
from typing import Optional
from config import DATA_DIR, BLOCKED_EXTENSIONS, TRASH_DIR_NAME


def _resolve_path(relative_path: str) -> Path:
    """
    Resolve a user-facing relative path to an absolute path under DATA_DIR.
    Prevents directory traversal attacks.
    """
    # Normalize and remove leading slash
    clean = relative_path.replace("\\", "/").lstrip("/")
    resolved = (DATA_DIR / clean).resolve()
    # Ensure the resolved path is still under DATA_DIR
    if not str(resolved).startswith(str(DATA_DIR.resolve())):
        raise ValueError("Path traversal detected")
    return resolved


def _ensure_safe_path(relative_path: str) -> Path:
    """Resolve and ensure path exists (for read operations)."""
    p = _resolve_path(relative_path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {relative_path}")
    return p


def is_blocked_extension(filename: str) -> bool:
    """Check if a file extension is blocked."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in BLOCKED_EXTENSIONS


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}PB"


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def list_files(
    relative_path: str = "",
    page: int = 1,
    size: int = 50,
    sort: str = "name",
) -> dict:
    """
    List files and directories at a given path.
    Returns dict with 'items' and 'total'.
    """
    target = _resolve_path(relative_path)
    if not target.is_dir():
        raise ValueError(f"Not a directory: {relative_path}")

    items = []
    try:
        for entry in target.iterdir():
            if entry.name == TRASH_DIR_NAME:
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "size_display": format_size(stat.st_size) if entry.is_file() else "-",
                "mtime": stat.st_mtime,
                "mtime_display": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)
                ),
            })
    except PermissionError:
        raise PermissionError(f"Permission denied: {relative_path}")

    # Sort
    if sort == "name":
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    elif sort == "size":
        items.sort(key=lambda x: (not x["is_dir"], x["size"]))
    elif sort == "time":
        items.sort(key=lambda x: (not x["is_dir"], -x["mtime"]))
    else:
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    total = len(items)
    start = (page - 1) * size
    end = start + size
    items = items[start:end]

    return {"items": items, "total": total, "page": page, "size": size}


def upload_file(
    file_content: bytes,
    filename: str,
    relative_path: str,
    expected_sha256: Optional[str] = None,
) -> dict:
    """
    Save an uploaded file. Returns result dict.
    """
    # Security check
    if is_blocked_extension(filename):
        return {
            "success": False,
            "error": f"File type blocked for security: {os.path.splitext(filename)[1]}",
            "sha256_match": None,
        }

    target_dir = _resolve_path(relative_path)
    if not target_dir.is_dir():
        raise ValueError(f"Target directory not found: {relative_path}")

    # Write to .tmp first
    tmp_path = target_dir / (filename + ".tmp")
    final_path = target_dir / filename

    try:
        with open(tmp_path, "wb") as f:
            f.write(file_content)

        # Compute SHA-256 on saved file
        actual_sha256 = compute_sha256(tmp_path)

        # Compare if client provided expected hash
        sha256_match = None
        if expected_sha256:
            sha256_match = actual_sha256 == expected_sha256

        # Rename .tmp → final
        tmp_path.rename(final_path)

        return {
            "success": True,
            "filename": filename,
            "sha256": actual_sha256,
            "sha256_match": sha256_match,
            "size": len(file_content),
            "size_display": format_size(len(file_content)),
        }
    except Exception as e:
        # Clean up tmp on failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise e


def download_file(relative_path: str) -> tuple[Path, str]:
    """
    Resolve a file for download. Returns (absolute_path, filename).
    """
    p = _ensure_safe_path(relative_path)
    if p.is_dir():
        raise ValueError(f"Cannot download a directory: {relative_path}")
    return p, p.name


def mkdir(relative_path: str, name: str) -> dict:
    """Create a new directory."""
    # Sanitize name
    name = name.strip().replace("/", "_").replace("\\", "_")
    if not name:
        raise ValueError("Directory name cannot be empty")

    parent = _resolve_path(relative_path)
    if not parent.is_dir():
        raise ValueError(f"Parent directory not found: {relative_path}")

    new_dir = parent / name
    if new_dir.exists():
        raise FileExistsError(f"Already exists: {name}")

    new_dir.mkdir(parents=True)
    return {"success": True, "name": name}


def rename(relative_path: str, new_name: str) -> dict:
    """Rename a file or directory."""
    new_name = new_name.strip().replace("/", "_").replace("\\", "_")
    if not new_name:
        raise ValueError("New name cannot be empty")

    p = _ensure_safe_path(relative_path)
    new_path = p.parent / new_name

    if new_path.exists():
        raise FileExistsError(f"Already exists: {new_name}")

    p.rename(new_path)
    return {"success": True, "new_name": new_name}


def delete(relative_path: str) -> dict:
    """
    Soft-delete: move to .trash directory.
    """
    p = _ensure_safe_path(relative_path)
    trash_dir = DATA_DIR / TRASH_DIR_NAME
    trash_dir.mkdir(exist_ok=True)

    # Use a timestamped name to avoid collisions in trash
    timestamp = int(time.time())
    trash_name = f"{timestamp}_{p.name}"
    trash_path = trash_dir / trash_name

    shutil.move(str(p), str(trash_path))
    return {"success": True, "name": p.name}


def cleanup_tmp_files():
    """Remove stale .tmp files older than 30 minutes."""
    cutoff = time.time() - 30 * 60
    for root, dirs, files in os.walk(DATA_DIR):
        # Skip trash directory
        if TRASH_DIR_NAME in root.split(os.sep):
            continue
        for f in files:
            if f.endswith(".tmp"):
                fp = Path(root) / f
                try:
                    if fp.stat().st_mtime < cutoff:
                        fp.unlink()
                        print(f"[Cleanup] Removed stale tmp: {fp}")
                except OSError:
                    pass
