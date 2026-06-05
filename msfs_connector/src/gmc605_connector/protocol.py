from __future__ import annotations

import json
from typing import Any

from .model import PROTOCOL_VERSION, Command


class ProtocolError(ValueError):
    pass


def encode_message(message: dict[str, Any]) -> bytes:
    return (
        json.dumps(message, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("ascii")


def decode_message(line: bytes | str) -> dict[str, Any]:
    try:
        text = line.decode("utf-8") if isinstance(line, bytes) else line
        message = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"invalid JSON message: {exc}") from exc

    if not isinstance(message, dict):
        raise ProtocolError("message must be a JSON object")
    if message.get("v") != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version: {message.get('v')!r}")
    if not isinstance(message.get("type"), str):
        raise ProtocolError("message type is required")
    return message


def parse_command(message: dict[str, Any]) -> Command:
    if message.get("type") != "command":
        raise ProtocolError("message is not a command")

    command = message.get("command")
    seq = message.get("seq")
    if not isinstance(command, str) or not command:
        raise ProtocolError("command name is required")
    if not isinstance(seq, int):
        raise ProtocolError("command seq must be an integer")

    return Command(seq=seq, command=command.upper(), value=message.get("value"))


def hello_message(source: str, update_hz: float) -> dict[str, Any]:
    return {
        "v": PROTOCOL_VERSION,
        "type": "hello",
        "role": "host_connector",
        "source": source,
        "update_hz": update_hz,
    }


def error_message(message: str) -> dict[str, Any]:
    return {
        "v": PROTOCOL_VERSION,
        "type": "error",
        "message": message,
    }

