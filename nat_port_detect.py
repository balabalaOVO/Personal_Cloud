#!/usr/bin/env python3
"""Detect the public IP and port assigned by NAT via STUN protocol."""

import socket
import struct
import hashlib
import hmac
import secrets


def stun_bind_request(stun_server: str, stun_port: int = 3478, timeout: float = 5.0) -> tuple[str, int] | None:
    """
    Send a STUN Binding Request to a STUN server and parse the XOR-MAPPED-ADDRESS
    from the response to get the NAT-assigned public IP and port.
    """
    BINDING_REQUEST = 0x0001
    MAGIC_COOKIE = 0x2112A442

    # Transaction ID: 12 random bytes
    transaction_id = secrets.token_bytes(12)

    # Build STUN header: type(2) + length(2) + magic_cookie(4) + transaction_id(12)
    header = struct.pack("!HHI", BINDING_REQUEST, 0, MAGIC_COOKIE) + transaction_id

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    try:
        addr = (socket.gethostbyname(stun_server), stun_port)
        sock.sendto(header, addr)

        data, _ = sock.recvfrom(2048)
        if len(data) < 20:
            return None

        msg_type, msg_length = struct.unpack("!HH", data[:4])
        msg_cookie = struct.unpack("!I", data[4:8])[0]
        msg_tid = data[8:20]

        # Verify it's a Binding Success Response (0x0101) with matching transaction ID
        if msg_type != 0x0101 or msg_tid != transaction_id:
            return None

        # Parse attributes
        offset = 20
        while offset + 4 <= len(data):
            attr_type, attr_len = struct.unpack("!HH", data[offset:offset + 4])
            offset += 4

            if attr_type == 0x0020:  # XOR-MAPPED-ADDRESS
                # family(1) + xor_port(2) + xor_ip(4)
                if offset + 8 > len(data):
                    break
                _family = data[offset]
                xor_port = struct.unpack("!H", data[offset + 2:offset + 4])[0]
                xor_ip = struct.unpack("!I", data[offset + 4:offset + 8])[0]

                port = xor_port ^ (MAGIC_COOKIE >> 16)
                ip_int = xor_ip ^ MAGIC_COOKIE
                ip = socket.inet_ntoa(struct.pack("!I", ip_int))

                return ip, port

            offset += attr_len
            # Align to 4-byte boundary
            if attr_len % 4:
                offset += 4 - (attr_len % 4)

        return None
    except socket.timeout:
        return None
    finally:
        sock.close()


def main():
    # Google's public STUN servers
    stun_servers = [
        ("stun.l.google.com", 19302),
        ("stun1.l.google.com", 19302),
        ("stun2.l.google.com", 19302),
    ]

    local_ip = None
    local_port = None

    # Quick local socket check
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 53))
            local_ip = s.getsockname()[0]
            local_port = s.getsockname()[1]
    except OSError:
        pass

    print("=" * 50)
    print("NAT Port Detection")
    print("=" * 50)

    if local_ip:
        print(f"Local IP (bound):    {local_ip}:{local_port}")

    for host, port in stun_servers:
        result = stun_bind_request(host, port)
        if result:
            public_ip, public_port = result
            print(f"STUN Server:          {host}:{port}")
            print(f"Public IP (NAT):      {public_ip}")
            print(f"Public Port (NAT):    {public_port}")
            print("-" * 50)
            return
        else:
            print(f"STUN Server:          {host}:{port}  ->  no response")

    print("All STUN servers unreachable. Check network/firewall.")


if __name__ == "__main__":
    main()
