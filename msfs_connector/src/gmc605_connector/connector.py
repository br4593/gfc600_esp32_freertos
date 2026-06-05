from __future__ import annotations

import logging
import time

from .protocol import ProtocolError, error_message, hello_message, parse_command
from .source import SnapshotSource
from .transport import Transport

LOGGER = logging.getLogger(__name__)


class Connector:
    def __init__(
        self,
        source: SnapshotSource,
        transport: Transport,
        update_hz: float = 10.0,
        snapshot_count: int | None = None,
    ) -> None:
        if update_hz <= 0:
            raise ValueError("update_hz must be greater than zero")
        if snapshot_count is not None and snapshot_count <= 0:
            raise ValueError("snapshot_count must be greater than zero")
        self._source = source
        self._transport = transport
        self._update_hz = update_hz
        self._snapshot_count = snapshot_count
        self._snapshot_seq = 0
        self._running = False

    def run(self) -> None:
        period_s = 1.0 / self._update_hz
        next_snapshot = time.monotonic()
        self._running = True

        self._transport.open()
        try:
            self._source.open()
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
            self._source.close()
            self._transport.close()

    def stop(self) -> None:
        self._running = False

    def process_incoming(self) -> None:
        for message in self._transport.receive():
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
