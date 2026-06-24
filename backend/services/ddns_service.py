"""
AI Personal Cloud Drive - DDNS service (Cloudflare)

Detects public IPv6 address and updates the AAAA record via Cloudflare API.

Detection strategy (tries in order):
  1. Connect to an external IPv6 host to discover the actual outgoing IPv6
  2. Fall back to external API (api6.ipify.org, ipv6.icanhazip.com)
  3. Fall back to local interface scan

Cloudflare API docs: https://developers.cloudflare.com/api/
"""

import asyncio
import json
import socket
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from config import (
    DDNS_CHECK_INTERVAL,
    DDNS_DOMAIN,
    DDNS_TTL,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_ZONE_ID,
)

CF_API_BASE = "https://api.cloudflare.com/client/v4"


class DDNSState:
    def __init__(self):
        self.current_ipv6: str | None = None
        self.last_check: float | None = None
        self.last_update: float | None = None
        self.last_error: str | None = None
        self.consecutive_failures: int = 0


_state = DDNSState()


# ═══════════════════════════════════════════════════════════════
#  IPv6 Detection
# ═══════════════════════════════════════════════════════════════

def _get_outgoing_ipv6() -> str | None:
    """Get public IPv6 by connecting to an external host and reading the local sockname."""
    try:
        addrinfo = socket.getaddrinfo("api6.ipify.org", 80, socket.AF_INET6, socket.SOCK_STREAM)
        for family, socktype, proto, canonname, sockaddr in addrinfo:
            addr, port, flowinfo, scope_id = sockaddr
            if addr.startswith("fe80:") or addr == "::1":
                continue
            if "%" in addr:
                addr = addr.split("%")[0]
            try:
                s = socket.socket(family, socktype, proto)
                s.settimeout(3)
                s.connect((addr, port))
                local_addr = s.getsockname()[0]
                s.close()
                if ":" in local_addr and not local_addr.startswith("fe80:"):
                    return local_addr
            except (socket.timeout, OSError):
                continue
    except socket.gaierror:
        pass
    return None


def _get_ipv6_from_api(url: str) -> str | None:
    """Get public IPv6 from an external web API."""
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=10) as resp:
            ip = resp.read().decode("utf-8").strip()
            if ip and ":" in ip and not ip.startswith("fe80:"):
                return ip
    except Exception:
        pass
    return None


def _scan_local_interfaces() -> str | None:
    """Fallback: scan local network interfaces for a public IPv6 address."""
    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET6
        ):
            addr = sockaddr[0]
            if "%" in addr:
                addr = addr.split("%")[0]
            if addr == "::1" or addr.startswith("fe80:") or addr.startswith("fc") or addr.startswith("fd"):
                continue
            return addr
    except socket.gaierror:
        pass
    return None


def get_public_ipv6() -> str | None:
    ip = _get_outgoing_ipv6()
    if ip:
        return ip
    for api in [
        "https://api6.ipify.org?format=text",
        "https://ipv6.icanhazip.com",
        "https://ifconfig.co/ip",
    ]:
        ip = _get_ipv6_from_api(api)
        if ip:
            return ip
    return _scan_local_interfaces()


# ═══════════════════════════════════════════════════════════════
#  Cloudflare API
# ═══════════════════════════════════════════════════════════════

def _cf_request(method: str, path: str, body: dict | None = None) -> dict:
    """
    Make a Cloudflare API request. Returns parsed JSON response.
    Raises RuntimeError on auth/config issues, HTTPError on network issues.
    """
    if not CLOUDFLARE_API_TOKEN:
        raise RuntimeError("CLOUDFLARE_API_TOKEN not configured")
    if not CLOUDFLARE_ZONE_ID:
        raise RuntimeError("CLOUDFLARE_ZONE_ID not configured")

    url = f"{CF_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _cf_is_success(resp: dict) -> bool:
    """Check if a Cloudflare API response indicates success."""
    return resp.get("success", False)


def _cf_error_message(resp: dict) -> str:
    """Extract error message from a Cloudflare API response."""
    errors = resp.get("errors", [])
    if errors:
        return "; ".join(f"{e.get('code', '?')}: {e.get('message', '?')}" for e in errors)
    return "Unknown error"


def get_remote_dns_record() -> dict | None:
    """
    Query the current AAAA record from Cloudflare.
    Returns record dict or None if not found / error.
    """
    try:
        resp = _cf_request(
            "GET",
            f"/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
            f"?type=AAAA&name={DDNS_DOMAIN}"
        )
        if not _cf_is_success(resp):
            _state.last_error = _cf_error_message(resp)
            return None
        records = resp.get("result", [])
        return records[0] if records else None
    except HTTPError as e:
        _state.last_error = f"HTTP {e.code}: {e.reason}"
        return None
    except Exception as e:
        _state.last_error = str(e)
        return None


def update_dns_record(ipv6: str) -> bool:
    """
    Update (or create) the AAAA record for DDNS_DOMAIN to the given IPv6 address.
    Cloudflare proxying is DISABLED so the raw IPv6 is exposed directly.
    """
    try:
        existing = get_remote_dns_record()

        if existing:
            record_id = existing["id"]
            resp = _cf_request(
                "PATCH",
                f"/zones/{CLOUDFLARE_ZONE_ID}/dns_records/{record_id}",
                {
                    "content": ipv6,
                    "ttl": DDNS_TTL,
                    "proxied": False,
                },
            )
        else:
            resp = _cf_request(
                "POST",
                f"/zones/{CLOUDFLARE_ZONE_ID}/dns_records",
                {
                    "type": "AAAA",
                    "name": DDNS_DOMAIN,
                    "content": ipv6,
                    "ttl": DDNS_TTL,
                    "proxied": False,
                },
            )

        if not _cf_is_success(resp):
            _state.last_error = _cf_error_message(resp)
            _state.consecutive_failures += 1
            return False

        _state.consecutive_failures = 0
        return True
    except HTTPError as e:
        _state.last_error = f"HTTP {e.code}: {e.reason}"
        _state.consecutive_failures += 1
        return False
    except Exception as e:
        _state.last_error = str(e)
        _state.consecutive_failures += 1
        return False


# ═══════════════════════════════════════════════════════════════
#  Background loop
# ═══════════════════════════════════════════════════════════════

async def ddns_check_loop():
    """
    Background task: periodically check IPv6 and update DNS.

    Triggers DNS update when EITHER:
      A) Local IPv6 changed (hotspot reconnected / IP rotated)
      B) Remote DNS record doesn't match local (manual change, stale record)
    """
    await asyncio.sleep(2)
    verify_countdown = 0

    while True:
        try:
            _state.last_check = time.time()
            ipv6 = get_public_ipv6()

            if not ipv6:
                if _state.consecutive_failures % 5 == 0:
                    print("[DDNS] WARN - No public IPv6 detected. Hotspot connected?")
                await asyncio.sleep(DDNS_CHECK_INTERVAL)
                continue

            need_update = False
            reason = ""

            # Condition A: local IP changed
            if ipv6 != _state.current_ipv6:
                need_update = True
                reason = f"Local IPv6 changed: {_state.current_ipv6} -> {ipv6}"

            # Condition B: periodic remote verification
            if not need_update and CLOUDFLARE_API_TOKEN:
                verify_countdown -= 1
                if verify_countdown <= 0:
                    verify_countdown = 6  # every ~6 checks
                    remote = get_remote_dns_record()
                    if remote:
                        remote_ip = remote.get("content", "")
                        if remote_ip != ipv6:
                            need_update = True
                            reason = f"Remote mismatch: {remote_ip} vs {ipv6}"
                        else:
                            _state.consecutive_failures = 0
                    else:
                        need_update = True
                        reason = f"No AAAA record for {DDNS_DOMAIN}"

            if need_update:
                print(f"\n[DDNS] {reason}")
                if CLOUDFLARE_API_TOKEN:
                    if update_dns_record(ipv6):
                        _state.current_ipv6 = ipv6
                        _state.last_update = time.time()
                        print(f"[DDNS] OK - {DDNS_DOMAIN} -> {ipv6}")
                    else:
                        print(f"[DDNS] FAIL - {_state.last_error}")
                else:
                    _state.current_ipv6 = ipv6
                    _state.last_update = time.time()
                    print(f"[DDNS] INFO - API token not set, tracking only: {ipv6}")

        except Exception as e:
            _state.last_error = str(e)
            _state.consecutive_failures += 1
            print(f"[DDNS] Error: {e}")

        await asyncio.sleep(DDNS_CHECK_INTERVAL)


def get_ddns_status() -> dict:
    return {
        "ipv6": _state.current_ipv6,
        "last_check": (
            datetime.fromtimestamp(_state.last_check).isoformat()
            if _state.last_check else None
        ),
        "last_update": (
            datetime.fromtimestamp(_state.last_update).isoformat()
            if _state.last_update else None
        ),
        "last_error": _state.last_error,
        "domain": DDNS_DOMAIN,
        "api_configured": bool(CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID),
        "provider": "cloudflare",
    }
