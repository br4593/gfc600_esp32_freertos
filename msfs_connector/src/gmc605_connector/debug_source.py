from __future__ import annotations

import copy
import math

from .model import (
    AircraftData,
    Command,
    CommandResult,
    Deviation,
    PanelSnapshot,
    References,
    normalize_heading,
)
from .source import SnapshotSource


class DebugSource(SnapshotSource):
    name = "debug"

    _LATERAL_MODES = {
        "NONE", "ROL", "HDG", "GPS", "VOR", "LOC", "VAPP", "BC", "LVL", "GA",
    }
    _VERTICAL_MODES = {
        "NONE", "PIT", "ALT", "ALTS", "VS", "IAS", "FLC", "VPTH",
        "ALTV", "GP", "GS", "LVL", "GA",
    }
    _VERTICAL_ARMED_MODES = {"ALT", "ALTS", "VPTH", "ALTV", "GP", "GS"}
    _NAV_SOURCES = {"NONE", "GPS", "VOR", "LOC"}

    def __init__(self) -> None:
        self._snapshot = self._default_snapshot()

    def open(self) -> None:
        return None

    def close(self) -> None:
        return None

    def poll(self) -> PanelSnapshot:
        return copy.deepcopy(self._snapshot)

    def handle_command(self, command: Command) -> CommandResult:
        handler = getattr(self, f"_command_{command.command.lower()}", None)
        if handler is None:
            return self._result(command, False, "unsupported debug command")

        try:
            handler(command.value)
        except (TypeError, ValueError) as exc:
            return self._result(command, False, str(exc))
        return self._result(command, True, "applied to debug state")

    def _default_snapshot(self) -> PanelSnapshot:
        return PanelSnapshot(
            source=self.name,
            sim_connected=True,
            cdi=Deviation.from_needle(False, 0),
            gsi=Deviation.from_needle(False, 0),
            references=References(
                heading_deg=90,
                altitude_ft=5000,
                vs_fpm=500,
                speed_kt=120,
            ),
            aircraft=AircraftData(
                heading_deg=90,
                altitude_ft=3000,
                vs_fpm=0,
                airspeed_kt=110,
            ),
            messages=["DEBUG"],
        )

    def _result(
        self, command: Command, accepted: bool, message: str
    ) -> CommandResult:
        return CommandResult(
            command_seq=command.seq,
            command=command.command,
            accepted=accepted,
            message=message,
        )

    def _ensure_fd_defaults(self) -> None:
        snapshot = self._snapshot
        if not snapshot.fd:
            snapshot.fd = True
        if snapshot.lat_active == "NONE":
            snapshot.lat_active = "ROL"
        if snapshot.vert_active == "NONE":
            snapshot.vert_active = "PIT"

    def _nav_mode(self, approach: bool) -> str:
        source = self._snapshot.nav_source
        if source == "NONE":
            raise ValueError("no valid navigation source")
        if approach and source == "VOR":
            return "VAPP"
        return source

    def _select_lateral_capture(self, mode: str) -> None:
        snapshot = self._snapshot
        self._ensure_fd_defaults()
        if not snapshot.cdi.valid:
            raise ValueError("CDI data is invalid")

        if snapshot.lat_active == mode:
            snapshot.lat_active = "ROL"
            snapshot.lat_armed = "NONE"
            return
        if snapshot.lat_armed == mode:
            snapshot.lat_armed = "NONE"
            return

        if snapshot.cdi.half_scale == "LESS":
            snapshot.lat_active = mode
            snapshot.lat_armed = "NONE"
        else:
            snapshot.lat_armed = mode

    def _set_vertical_active(self, mode: str, arm_alts: bool = True) -> None:
        snapshot = self._snapshot
        self._ensure_fd_defaults()
        if snapshot.vert_active == mode:
            snapshot.vert_active = "PIT"
        else:
            snapshot.vert_active = mode
        if arm_alts:
            self._add_vert_armed("ALTS")

    def _add_vert_armed(self, mode: str) -> None:
        if mode not in self._snapshot.vert_armed:
            self._snapshot.vert_armed.append(mode)

    def _remove_vert_armed(self, mode: str) -> None:
        if mode in self._snapshot.vert_armed:
            self._snapshot.vert_armed.remove(mode)

    def _command_debug_reset(self, value: object) -> None:
        self._snapshot = self._default_snapshot()

    def _command_debug_set_nav_source(self, value: object) -> None:
        source = self._mode_value(value, self._NAV_SOURCES, "nav source")
        self._snapshot.nav_source = source

    def _command_debug_set_snapshot(self, value: object) -> None:
        if not isinstance(value, dict):
            raise ValueError("snapshot override value must be an object")

        snapshot = copy.deepcopy(self._snapshot)
        self._apply_snapshot_override(snapshot, value)
        self._normalize_snapshot(snapshot)
        self._snapshot = snapshot

    def _command_debug_set_simvars(self, value: object) -> None:
        if not isinstance(value, dict):
            raise ValueError("SimVar value must be an object")
        from .msfs_source import derive_snapshot

        snapshot = derive_snapshot(value)
        snapshot.source = self.name
        snapshot.messages = ["DEBUG SIMVARS"]
        self._snapshot = snapshot

    def _apply_snapshot_override(
        self, snapshot: PanelSnapshot, value: dict[str, object]
    ) -> None:
        for name in ("sim_connected", "ap", "fd", "yd"):
            if name in value:
                setattr(snapshot, name, self._bool_value(value[name], name))

        if "lat_active" in value:
            snapshot.lat_active = self._mode_value(
                value["lat_active"], self._LATERAL_MODES, "lat_active"
            )
        if "lat_armed" in value:
            snapshot.lat_armed = self._mode_value(
                value["lat_armed"], self._LATERAL_MODES, "lat_armed"
            )
        if "vert_active" in value:
            snapshot.vert_active = self._mode_value(
                value["vert_active"], self._VERTICAL_MODES, "vert_active"
            )
        if "vert_armed" in value:
            if not isinstance(value["vert_armed"], list):
                raise ValueError("vert_armed must be a list")
            snapshot.vert_armed = []
            for mode in value["vert_armed"]:
                armed_mode = self._mode_value(
                    mode,
                    self._VERTICAL_ARMED_MODES | {"NONE"},
                    "vert_armed",
                )
                if armed_mode != "NONE" and armed_mode not in snapshot.vert_armed:
                    snapshot.vert_armed.append(armed_mode)
        if "nav_source" in value:
            snapshot.nav_source = self._mode_value(
                value["nav_source"], self._NAV_SOURCES, "nav_source"
            )

        if "cdi" in value:
            snapshot.cdi = self._deviation_value(value["cdi"], "cdi")
        if "gsi" in value:
            snapshot.gsi = self._deviation_value(value["gsi"], "gsi")

        references = value.get("references")
        if "references" in value and not isinstance(references, dict):
            raise ValueError("references must be an object")
        if isinstance(references, dict):
            if "heading_deg" in references:
                snapshot.references.heading_deg = normalize_heading(
                    self._int_value(references["heading_deg"], "references.heading_deg")
                )
            if "altitude_ft" in references:
                snapshot.references.altitude_ft = self._int_value(
                    references["altitude_ft"], "references.altitude_ft"
                )
            if "vs_fpm" in references:
                snapshot.references.vs_fpm = self._int_value(
                    references["vs_fpm"], "references.vs_fpm"
                )
            if "speed_kt" in references:
                snapshot.references.speed_kt = max(
                    0, self._int_value(references["speed_kt"], "references.speed_kt")
                )

        aircraft = value.get("aircraft")
        if "aircraft" in value and not isinstance(aircraft, dict):
            raise ValueError("aircraft must be an object")
        if isinstance(aircraft, dict):
            if "heading_deg" in aircraft:
                snapshot.aircraft.heading_deg = normalize_heading(
                    self._int_value(aircraft["heading_deg"], "aircraft.heading_deg")
                )
            if "altitude_ft" in aircraft:
                snapshot.aircraft.altitude_ft = self._int_value(
                    aircraft["altitude_ft"], "aircraft.altitude_ft"
                )
            if "vs_fpm" in aircraft:
                snapshot.aircraft.vs_fpm = self._int_value(
                    aircraft["vs_fpm"], "aircraft.vs_fpm"
                )
            if "airspeed_kt" in aircraft:
                snapshot.aircraft.airspeed_kt = max(
                    0, self._int_value(aircraft["airspeed_kt"], "aircraft.airspeed_kt")
                )

        if "messages" in value:
            snapshot.messages = self._string_list(value["messages"], "messages", 4)
        if "pending_commands" in value:
            snapshot.pending_commands = self._string_list(
                value["pending_commands"], "pending_commands", 8
            )

    def _mode_value(self, value: object, allowed: set[str], field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")
        mode = value.upper()
        if mode not in allowed:
            raise ValueError(f"{field_name} has unsupported value {mode}")
        return mode

    def _bool_value(self, value: object, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{field_name} must be a boolean")
        return value

    def _int_value(self, value: object, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} must be a number")
        if not math.isfinite(float(value)):
            raise ValueError(f"{field_name} must be finite")
        return int(round(float(value)))

    def _string_list(self, value: object, field_name: str, limit: int) -> list[str]:
        if not isinstance(value, list):
            raise ValueError(f"{field_name} must be a list")
        if not all(isinstance(item, str) for item in value):
            raise ValueError(f"{field_name} entries must be strings")
        return [item[:32] for item in value[:limit]]

    def _normalize_snapshot(self, snapshot: PanelSnapshot) -> None:
        if snapshot.ap:
            snapshot.fd = True
        if not snapshot.fd:
            snapshot.lat_active = "NONE"
            snapshot.lat_armed = "NONE"
            snapshot.vert_active = "NONE"
            snapshot.vert_armed.clear()
            return
        if snapshot.lat_active == "NONE":
            snapshot.lat_active = "ROL"
        if snapshot.vert_active == "NONE":
            snapshot.vert_active = "PIT"

    def _deviation_value(self, value: object, field_name: str) -> Deviation:
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object")
        return Deviation.from_needle(
            self._bool_value(value.get("valid", False), f"{field_name}.valid"),
            self._int_value(value.get("needle", 0), f"{field_name}.needle"),
        )

    def _command_debug_set_cdi(self, value: object) -> None:
        self._snapshot.cdi = Deviation.from_needle(
            True, self._int_value(value, "CDI needle")
        )

    def _command_debug_set_gsi(self, value: object) -> None:
        self._snapshot.gsi = Deviation.from_needle(
            True, self._int_value(value, "GSI needle")
        )

    def _command_debug_capture_lateral(self, value: object) -> None:
        snapshot = self._snapshot
        if snapshot.lat_armed == "NONE":
            raise ValueError("no lateral mode is armed")
        snapshot.lat_active = snapshot.lat_armed
        snapshot.lat_armed = "NONE"

    def _command_debug_capture_vertical(self, value: object) -> None:
        snapshot = self._snapshot
        if not snapshot.vert_armed:
            raise ValueError("no vertical mode is armed")

        for mode in ("GP", "GS", "VPTH", "ALTS", "ALT", "ALTV"):
            if mode not in snapshot.vert_armed:
                continue
            self._remove_vert_armed(mode)
            snapshot.vert_active = mode
            if mode == "ALTS":
                self._add_vert_armed("ALT")
            return

    def _command_ap_press(self, value: object) -> None:
        snapshot = self._snapshot
        if snapshot.ap:
            snapshot.ap = False
            return
        snapshot.ap = True
        self._ensure_fd_defaults()

    def _command_fd_press(self, value: object) -> None:
        snapshot = self._snapshot
        if snapshot.ap:
            raise ValueError("FD key is disabled while AP is engaged")
        if snapshot.fd:
            snapshot.fd = False
            snapshot.lat_active = "NONE"
            snapshot.lat_armed = "NONE"
            snapshot.vert_active = "NONE"
            snapshot.vert_armed.clear()
            return
        self._ensure_fd_defaults()

    def _command_yd_press(self, value: object) -> None:
        self._snapshot.yd = not self._snapshot.yd

    def _command_ap_disconnect(self, value: object) -> None:
        self._snapshot.ap = False

    def _command_hdg_press(self, value: object) -> None:
        snapshot = self._snapshot
        self._ensure_fd_defaults()
        snapshot.lat_active = "ROL" if snapshot.lat_active == "HDG" else "HDG"

    def _command_nav_press(self, value: object) -> None:
        self._select_lateral_capture(self._nav_mode(approach=False))
        if self._snapshot.nav_source == "GPS":
            self._remove_vert_armed("GP")
        if self._snapshot.nav_source == "LOC":
            self._remove_vert_armed("GS")

    def _command_apr_press(self, value: object) -> None:
        mode = self._nav_mode(approach=True)
        was_selected = (
            self._snapshot.lat_active == mode or self._snapshot.lat_armed == mode
        )
        self._select_lateral_capture(mode)
        vertical_mode = {
            "GPS": "GP",
            "LOC": "GS",
        }.get(self._snapshot.nav_source)
        if was_selected:
            if vertical_mode is not None:
                self._remove_vert_armed(vertical_mode)
            if vertical_mode is not None and self._snapshot.vert_active == vertical_mode:
                self._snapshot.vert_active = "PIT"
            return
        if self._snapshot.nav_source == "GPS":
            self._add_vert_armed("GP")
        if self._snapshot.nav_source == "LOC":
            self._add_vert_armed("GS")

    def _command_bc_press(self, value: object) -> None:
        if self._snapshot.nav_source != "LOC":
            raise ValueError("BC requires a LOC source")
        self._select_lateral_capture("BC")

    def _command_alt_press(self, value: object) -> None:
        was_active = self._snapshot.vert_active == "ALT"
        self._set_vertical_active("ALT", arm_alts=False)
        if was_active:
            self._add_vert_armed("ALTS")
        else:
            self._remove_vert_armed("ALTS")
        self._remove_vert_armed("ALT")

    def _command_vs_press(self, value: object) -> None:
        self._set_vertical_active("VS")

    def _command_ias_press(self, value: object) -> None:
        self._set_vertical_active("IAS")

    def _command_flc_press(self, value: object) -> None:
        self._set_vertical_active("FLC")

    def _command_vnv_press(self, value: object) -> None:
        self._ensure_fd_defaults()
        if "VPTH" in self._snapshot.vert_armed:
            self._remove_vert_armed("VPTH")
        else:
            self._add_vert_armed("VPTH")

    def _command_lvl_press(self, value: object) -> None:
        snapshot = self._snapshot
        snapshot.ap = True
        snapshot.fd = True
        snapshot.lat_active = "LVL"
        snapshot.lat_armed = "NONE"
        snapshot.vert_active = "LVL"
        snapshot.vert_armed.clear()

    def _command_ga_press(self, value: object) -> None:
        snapshot = self._snapshot
        snapshot.fd = True
        snapshot.lat_active = "GA"
        snapshot.lat_armed = "NONE"
        snapshot.vert_active = "GA"
        snapshot.vert_armed.clear()
        self._add_vert_armed("ALTS")

    def _command_heading_set(self, value: object) -> None:
        self._snapshot.references.heading_deg = normalize_heading(
            self._int_value(value, "heading")
        )

    def _command_altitude_set(self, value: object) -> None:
        self._snapshot.references.altitude_ft = self._int_value(value, "altitude")

    def _command_vs_set(self, value: object) -> None:
        self._snapshot.references.vs_fpm = self._int_value(value, "vertical speed")

    def _command_speed_set(self, value: object) -> None:
        self._snapshot.references.speed_kt = max(
            0, self._int_value(value, "airspeed")
        )
