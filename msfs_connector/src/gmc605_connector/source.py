from __future__ import annotations

from abc import ABC, abstractmethod

from .model import Command, CommandResult, PanelSnapshot


class SnapshotSource(ABC):
    name: str

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def poll(self) -> PanelSnapshot:
        raise NotImplementedError

    @abstractmethod
    def handle_command(self, command: Command) -> CommandResult:
        raise NotImplementedError

