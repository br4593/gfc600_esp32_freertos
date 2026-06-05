from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PROTOCOL_VERSION = 1


@dataclass(slots=True)
class Deviation:
    valid: bool = False
    needle: int = 0
    half_scale: str = "INVALID"

    @classmethod
    def from_needle(cls, valid: bool, needle: int | float | None) -> "Deviation":
        normalized = clamp_needle(needle)
        if not valid:
            return cls(valid=False, needle=normalized, half_scale="INVALID")
        half_scale = "LESS" if abs(normalized) < 64 else "GREATER"
        return cls(valid=True, needle=normalized, half_scale=half_scale)


@dataclass(slots=True)
class References:
    heading_deg: int = 0
    altitude_ft: int = 0
    vs_fpm: int = 0
    speed_kt: int = 0


@dataclass(slots=True)
class AircraftData:
    heading_deg: int = 0
    altitude_ft: int = 0
    vs_fpm: int = 0
    airspeed_kt: int = 0


@dataclass(slots=True)
class PanelSnapshot:
    seq: int = 0
    timestamp_ms: int = 0
    source: str = "debug"
    sim_connected: bool = False
    ap: bool = False
    fd: bool = False
    yd: bool = False
    lat_active: str = "NONE"
    lat_armed: str = "NONE"
    vert_active: str = "NONE"
    vert_armed: list[str] = field(default_factory=list)
    nav_source: str = "NONE"
    cdi: Deviation = field(default_factory=Deviation)
    gsi: Deviation = field(default_factory=Deviation)
    references: References = field(default_factory=References)
    aircraft: AircraftData = field(default_factory=AircraftData)
    messages: list[str] = field(default_factory=list)
    pending_commands: list[str] = field(default_factory=list)

    def to_message(self) -> dict[str, Any]:
        return {
            "v": PROTOCOL_VERSION,
            "type": "snapshot",
            **asdict(self),
        }


@dataclass(slots=True)
class Command:
    seq: int
    command: str
    value: Any = None


@dataclass(slots=True)
class CommandResult:
    command_seq: int
    command: str
    accepted: bool
    message: str = ""

    def to_message(self) -> dict[str, Any]:
        return {
            "v": PROTOCOL_VERSION,
            "type": "command_result",
            "command_seq": self.command_seq,
            "command": self.command,
            "accepted": self.accepted,
            "message": self.message,
        }


def clamp_needle(value: int | float | None) -> int:
    if value is None:
        return 0
    return max(-127, min(127, int(round(float(value)))))


def normalize_heading(value: int | float | None) -> int:
    if value is None:
        return 0
    return int(round(float(value))) % 360


def to_bool(value: Any) -> bool:
    if value is None:
        return False
    return bool(value)


def to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default

