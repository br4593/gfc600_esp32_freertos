from __future__ import annotations

import logging

from .debug_source import DebugSource
from .model import Command, CommandResult, PanelSnapshot
from .msfs_source import MsfsSource
from .source import SnapshotSource

LOGGER = logging.getLogger(__name__)


class AutoSource(SnapshotSource):
    """Use MSFS when the simulator is running, otherwise fall back to debug.

    On ``open()`` the source attempts to connect to MSFS (which both reads
    SimVars and transmits key events, i.e. it *controls* the sim). If MSFS is
    not running, SimConnect raises and we transparently fall back to the
    in-memory debug source so the panel/web GUI still works.
    """

    name = "auto"

    def __init__(self, cache_ms: int = 100) -> None:
        self._cache_ms = cache_ms
        self._active: SnapshotSource | None = None

    def open(self) -> None:
        msfs = MsfsSource(cache_ms=self._cache_ms)
        try:
            msfs.open()
        except Exception as exc:
            LOGGER.info(
                "MSFS not available (%s); falling back to debug source", exc
            )
            try:
                msfs.close()
            except Exception:  # nothing meaningful to do on cleanup failure
                LOGGER.debug("MSFS cleanup after failed open errored", exc_info=True)
            debug = DebugSource()
            debug.open()
            self._active = debug
            self.name = debug.name
            return

        LOGGER.info("Connected to MSFS; connector will read and control the sim")
        self._active = msfs
        self.name = msfs.name

    def close(self) -> None:
        if self._active is not None:
            self._active.close()
        self._active = None
        self.name = "auto"

    def poll(self) -> PanelSnapshot:
        if self._active is None:
            raise RuntimeError("auto source is not open")
        return self._active.poll()

    def handle_command(self, command: Command) -> CommandResult:
        if self._active is None:
            return CommandResult(
                command_seq=command.seq,
                command=command.command,
                accepted=False,
                message="auto source is not open",
            )
        return self._active.handle_command(command)
