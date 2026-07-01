"""
AI Personal Cloud Drive - mDNS Service

Registers clouddrive.local on the local network so mobile devices
on the same hotspot can reach the server without DNS:
    https://clouddrive.local:8000

Supports HTTP (_http._tcp) and HTTPS (_https._tcp) service types.
Zero latency, zero public DNS lookups, zero manual IP entry.
"""

import socket
import struct
import time
from zeroconf import Zeroconf, ServiceInfo, IPVersion


# ── State ──────────────────────────────────────────────────────────

_mdns: Zeroconf | None = None
_service_info: ServiceInfo | None = None
_lan_ip: str | None = None
_mdns_name: str = "clouddrive"
_protocol: str = "http"


# ── LAN IP detection ───────────────────────────────────────────────

def get_lan_ip() -> str | None:
    """
    Find the LAN IPv4 address on the tethered hotspot interface.

    Strategy: look for the interface that has the default route
    (the one with internet access — i.e., the phone hotspot).
    """
    candidates = []

    # Scan all interfaces with assigned IPv4 addresses
    for iface_name, iface_addrs in _get_interfaces():
        for addr in iface_addrs:
            if addr.startswith("127.") or addr == "0.0.0.0":
                continue
            if addr.startswith("169.254."):  # APIPA, skip
                continue
            # hotspot networks typically use these ranges
            if (addr.startswith("192.168.") or
                addr.startswith("172.") or
                addr.startswith("10.")):
                candidates.append((iface_name, addr))

    if not candidates:
        return None

    # Prefer the interface that has internet connectivity
    # (i.e., the one with a default route that can reach 8.8.8.8)
    for iface_name, addr in candidates:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            if s.getsockname()[0] == addr:
                s.close()
                return addr
            s.close()
        except OSError:
            pass

    # Fallback: return the first non-APIPA address
    return candidates[0][1] if candidates else None


def _get_interfaces() -> list[tuple[str, list[str]]]:
    """
    Cross-platform interface enumeration.
    Returns [(name, [addr1, addr2, ...]), ...]
    """
    try:
        # Windows
        import ctypes
        return _get_interfaces_windows()
    except Exception:
        pass

    try:
        # Unix (Linux/macOS)
        return _get_interfaces_unix()
    except Exception:
        pass

    return []


def _get_interfaces_windows() -> list[tuple[str, list[str]]]:
    """Windows: use socket.gethostbyname_ex and netifaces-like scan."""
    return _get_interfaces_unix()


def _get_interfaces_unix() -> list[tuple[str, list[str]]]:
    """Enumerate IPv4 addresses per interface. Works on Windows too."""
    result: list[tuple[str, list[str]]] = []
    try:
        hostname = socket.gethostname()
        # Get all addresses
        addrs = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for family, _, _, _, sockaddr in addrs:
            ip = sockaddr[0]
            if not ip.startswith("127."):
                result.append(("auto", [ip]))
        # Deduplicate
        seen = set()
        deduped = []
        for name, ips in result:
            for ip in ips:
                if ip not in seen:
                    seen.add(ip)
                    deduped.append(ip)
        return [("auto", deduped)] if deduped else []
    except socket.gaierror:
        return []


# ── mDNS Registration ──────────────────────────────────────────────

def start_mdns(port: int, name: str = "clouddrive", protocol: str = "http") -> str | None:
    """
    Register clouddrive.local via mDNS on the LAN.

    Args:
        port: TCP port the server is listening on.
        name: mDNS hostname (without .local suffix).
        protocol: "http" or "https" — determines the advertised service type.

    Returns the LAN IP if successful, None otherwise.
    On iPhone hotspot (Safari), mDNS is natively supported.
    Android requires a workaround (shows LAN IP as fallback).
    """
    global _mdns, _service_info, _lan_ip, _mdns_name, _protocol

    _mdns_name = name
    _protocol = protocol

    # Detect LAN IP
    _lan_ip = get_lan_ip()
    if not _lan_ip:
        print("[mDNS] WARN - No LAN IP detected, skipping mDNS registration")
        return None

    print(f"[mDNS] LAN IP detected: {_lan_ip}")

    # Use appropriate service type: _https._tcp or _http._tcp
    service_type = f"_{protocol}._tcp.local."

    try:
        _mdns = Zeroconf(ip_version=IPVersion.V4Only)

        # mDNS service info
        _service_info = ServiceInfo(
            type_=service_type,
            name=f"{name}.{service_type}",
            addresses=[socket.inet_aton(_lan_ip)],
            port=port,
            properties={"path": "/"},
            server=f"{name}.local.",
        )

        _mdns.register_service(_service_info, allow_name_change=True)
        print(f"[mDNS] Registered: {protocol}://{name}.local:{port}")
        return _lan_ip

    except Exception as e:
        print(f"[mDNS] ERROR - {e}")
        _lan_ip = None
        return None


def stop_mdns():
    """Unregister mDNS service and clean up."""
    global _mdns, _service_info

    if _mdns and _service_info:
        try:
            _mdns.unregister_service(_service_info)
        except Exception:
            pass
    if _mdns:
        try:
            _mdns.close()
        except Exception:
            pass
    _mdns = None
    _service_info = None
    print("[mDNS] Unregistered")


def get_status() -> dict:
    """Return current mDNS status for API and startup display.
    Always re-detects LAN IP (IP may change between hotspot connections).
    """
    global _lan_ip
    _lan_ip = get_lan_ip()
    return {
        "enabled": _mdns is not None,
        "lan_ip": _lan_ip,
        "mdns_name": f"{_mdns_name}.local",
        "protocol": _protocol,
        "url": f"{_protocol}://{_mdns_name}.local" if _lan_ip else None,
        "lan_url": f"{_protocol}://{_lan_ip}" if _lan_ip else None,
    }
