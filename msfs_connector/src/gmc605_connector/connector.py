from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import TypeVar

from .protocol import ProtocolError, error_message, hello_message, parse_command
from .source import SnapshotSource
from .transport import Transport

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class Connector:
    def __init__(
        self,
        source: SnapshotSource,
        transport: Transport,
        update_hz: float = 10.0,
        snapshot_count: int | None = None,
        source_open_timeout_s: float = 5.0,
    ) -> None:
        if update_hz <= 0:
            raise ValueError("update_hz must be greater than zero")
        if snapshot_count is not None and snapshot_count <= 0:
            raise ValueError("snapshot_count must be greater than zero")
        if source_open_timeout_s <= 0:
            raise ValueError("source_open_timeout_s must be greater than zero")
        self._source = source
        self._transport = transport
        self._update_hz = update_hz
        self._snapshot_count = snapshot_count
        self._source_open_timeout_s = source_open_timeout_s
        self._snapshot_seq = 0
        self._running = False

    def run(self) -> None:
        period_s = 1.0 / self._update_hz
        next_snapshot = time.monotonic()
        self._running = True

        self._transport.open()
        try:
            run_with_timeout(
                self._source.open,
                self._source_open_timeout_s,
                f"{self._source.name} source open",
            )
            self._transport.send(hello_message(self._source.name, self._update_hz))

            while self._running:
                self.process_incoming()

                now = time.monotonic()
                if now >= next_snapshot:
                    self.send_snapshot()
                    if (
                        self._snapshot_count is not None
                        and self._snapshot_seq >= self._snapshot_count
                    ):
                        self.stop()
                    next_snapshot = now + period_s

                time.sleep(min(0.005, max(0.0, next_snapshot - time.monotonic())))
        finally:
            close_with_timeout(self._source.close, 1.0, f"{self._source.name} source")
            close_with_timeout(self._transport.close, 1.0, "transport")

    def stop(self) -> None:
        self._running = False

    def process_incoming(self) -> None:
        for message in self._transport.receive():
            if message.get("type") == "_transport_raw":
                continue
            if message.get("type") == "_transport_error":
                self._transport.send(error_message(str(message.get("message", ""))))
                continue

            try:
                command = parse_command(message)
            except ProtocolError as exc:
                self._transport.send(error_message(str(exc)))
                continue

            result = self._source.handle_command(command)
            self._transport.send(result.to_message())
            self.send_snapshot()

    def send_snapshot(self) -> None:
        try:
            snapshot = self._source.poll()
        except Exception as exc:
            LOGGER.exception("failed to poll snapshot source")
            self._transport.send(error_message(f"snapshot poll failed: {exc}"))
            return

        self._snapshot_seq += 1
        snapshot.seq = self._snapshot_seq
        snapshot.timestamp_ms = int(time.time() * 1000)
        self._transport.send(snapshot.to_message())


def run_with_timeout(action: Callable[[], T], timeout_s: float, label: str) -> T:
    """Run a potentially blocking third-party call with a bounded wait."""
    result: list[T] = []
    errors: list[BaseException] = []

    def target() -> None:
        try:
            result.append(action())
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=target, name=f"gmc605-{label}", daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)

    if thread.is_alive():
        raise TimeoutError(f"{label} timed out after {timeout_s:g} seconds")
    if errors:
        raise errors[0]
    return result[0] if result else None  # type: ignore[return-value]


def close_with_timeout(action: Callable[[], object], timeout_s: float, label: str) -> None:
    try:
        run_with_timeout(action, timeout_s, f"{label} close")
    except Exception as exc:
        LOGGER.warning("%s close did not complete cleanly: %s", label, exc)
