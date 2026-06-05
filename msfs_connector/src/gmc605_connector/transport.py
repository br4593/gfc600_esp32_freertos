from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Any

from .protocol import ProtocolError, decode_message, encode_message


class Transport(ABC):
    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send(self, message: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class SerialTransport(Transport):
    def __init__(self, port: str, baudrate: int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._serial: Any = None
        self._buffer = bytearray()

    def open(self) -> None:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError(
                "pyserial is required for UART transport; install the project dependencies"
            ) from exc

        self._serial = serial.serial_for_url(
            self._port,
            baudrate=self._baudrate,
            timeout=0,
            write_timeout=1,
        )

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def send(self, message: dict[str, Any]) -> None:
        if self._serial is None:
            raise RuntimeError("serial transport is not open")
        self._serial.write(encode_message(message))

    def receive(self) -> list[dict[str, Any]]:
        if self._serial is None:
            return []

        waiting = int(self._serial.in_waiting)
        if waiting:
            self._buffer.extend(self._serial.read(waiting))

        messages: list[dict[str, Any]] = []
        while b"\n" in self._buffer:
            line, _, remaining = self._buffer.partition(b"\n")
            self._buffer = bytearray(remaining)
            if not line.strip():
                continue
            try:
                messages.append(decode_message(line))
            except ProtocolError as exc:
                messages.append(
                    {
                        "v": 1,
                        "type": "_transport_error",
                        "message": str(exc),
                    }
                )
        return messages


class StdoutTransport(Transport):
    def open(self) -> None:
        return None

    def close(self) -> None:
        return None

    def send(self, message: dict[str, Any]) -> None:
        sys.stdout.buffer.write(encode_message(message))
        sys.stdout.buffer.flush()

    def receive(self) -> list[dict[str, Any]]:
        return []


class MemoryTransport(Transport):
    """Test transport."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.incoming: list[dict[str, Any]] = []

    def open(self) -> None:
        return None

    def close(self) -> None:
        return None

    def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)

    def receive(self) -> list[dict[str, Any]]:
        messages = self.incoming
        self.incoming = []
        return messages
