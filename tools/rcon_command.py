#!/usr/bin/env python3
"""Send one command to the local development server RCON endpoint."""

from __future__ import annotations

import argparse
import socket
import struct


def packet(request_id: int, kind: int, payload: str) -> bytes:
    body = struct.pack("<ii", request_id, kind) + payload.encode("utf-8") + b"\0\0"
    return struct.pack("<i", len(body)) + body


def receive(stream: socket.socket) -> tuple[int, int, str]:
    header = stream.recv(4)
    if len(header) != 4:
        raise RuntimeError("RCON connection closed before a packet header")
    size = struct.unpack("<i", header)[0]
    data = bytearray()
    while len(data) < size:
        block = stream.recv(size - len(data))
        if not block:
            raise RuntimeError("RCON connection closed mid-packet")
        data.extend(block)
    request_id, kind = struct.unpack("<ii", data[:8])
    return request_id, kind, bytes(data[8:-2]).decode("utf-8", "replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=25575)
    parser.add_argument("--password", default="seele_local_scout")
    args = parser.parse_args()
    with socket.create_connection((args.host, args.port), timeout=10) as stream:
        stream.sendall(packet(1, 3, args.password))
        auth_id, _kind, _text = receive(stream)
        if auth_id == -1:
            raise RuntimeError("RCON authentication failed")
        stream.sendall(packet(2, 2, args.command))
        response_id, _kind, text = receive(stream)
        if response_id != 2:
            raise RuntimeError(f"unexpected RCON response id: {response_id}")
        print(text)


if __name__ == "__main__":
    main()
