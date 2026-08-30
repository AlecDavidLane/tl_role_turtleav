#!/usr/bin/env python3
"""Idempotently configure a Turtle AV CHAZY Control Pro over its SSH CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time

try:
    import paramiko
except ImportError:
    print(
        json.dumps(
            {
                "error": "Missing Python dependency: paramiko. Run: python3 -m pip install -r requirements.txt"
            }
        )
    )
    raise SystemExit(2)


PROMPT = b"CONTROLLER>"
BAUD_TO_INDEX = {115200: 0, 57600: 1, 38400: 2, 19200: 3, 9600: 4}
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class ChazyError(RuntimeError):
    pass


def receive_until(channel, marker: bytes, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    chunks: list[bytes] = []
    while time.monotonic() < deadline:
        if channel.recv_ready():
            data = channel.recv(65535)
            if not data:
                break
            chunks.append(data)
            if marker in b"".join(chunks):
                return b"".join(chunks).decode("utf-8", errors="replace")
        else:
            time.sleep(0.05)
    output = b"".join(chunks).decode("utf-8", errors="replace")
    raise ChazyError(f"Timed out waiting for CHAZY prompt. Partial response: {output!r}")


def send_command(channel, command: str, timeout: float) -> str:
    channel.sendall((command + "\r\n").encode("ascii"))
    return receive_until(channel, PROMPT, timeout)


def parse_status(response: str) -> tuple[int, str]:
    normalized = ANSI_ESCAPE.sub("", response).replace("\x00", "")
    # Firmware versions have no five-digit integer, so matching any supported
    # baud value is both safer and more tolerant of firmware-specific spacing.
    baud_match = re.search(r"(?<!\d)(115200|57600|38400|19200|9600)(?!\d)", normalized)
    if not baud_match:
        compact = " ".join(normalized.split())
        raise ChazyError(
            f"Could not parse RS-232 baud rate from GET STATUS response: {compact[:1000]!r}"
        )

    firmware_match = re.search(r"FW Version:\s*([0-9.]+)", normalized)
    firmware = firmware_match.group(1) if firmware_match else "unknown"
    return int(baud_match.group(1)), firmware


def query_status(channel, timeout: float, attempts: int = 3) -> tuple[int, str]:
    last_error: ChazyError | None = None
    for attempt in range(attempts):
        response = send_command(channel, "GET STATUS", timeout)
        try:
            return parse_status(response)
        except ChazyError as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.3)
    assert last_error is not None
    raise last_error


def configure(args: argparse.Namespace) -> dict[str, object]:
    password = os.environ.get("CHAZY_PASSWORD")
    if not password:
        raise ChazyError("CHAZY_PASSWORD is not set")

    transport = paramiko.Transport((args.host, args.port))
    transport.banner_timeout = args.connect_timeout
    transport.auth_timeout = args.connect_timeout

    try:
        transport.connect(username=args.username, password=password)
        channel = transport.open_session(timeout=args.connect_timeout)
        # The CHAZY server intentionally rejects PTY requests. Open its restricted
        # command shell directly instead of treating it as a Linux host.
        channel.invoke_shell()
        receive_until(channel, PROMPT, args.command_timeout)

        before_baud, firmware = query_status(channel, args.command_timeout)
        changed = before_baud != args.desired_baud

        if changed:
            command = f"SET RS232BAUDRATE {BAUD_TO_INDEX[args.desired_baud]}"
            send_command(channel, command, args.command_timeout)

        after_baud, final_firmware = query_status(channel, args.command_timeout)
        verified = after_baud == args.desired_baud
        if not verified:
            raise ChazyError(
                f"Verification failed: requested {args.desired_baud}, controller returned {after_baud}"
            )

        return {
            "host": args.host,
            "firmware": final_firmware or firmware,
            "before_baud": before_baud,
            "after_baud": after_baud,
            "desired_baud": args.desired_baud,
            "changed": changed,
            "verified": verified,
        }
    finally:
        transport.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--desired-baud", type=int, choices=sorted(BAUD_TO_INDEX), required=True)
    parser.add_argument("--connect-timeout", type=float, default=10)
    parser.add_argument("--command-timeout", type=float, default=10)
    return parser.parse_args()


def main() -> int:
    try:
        result = configure(parse_args())
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ChazyError, paramiko.SSHException, socket.error, OSError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
