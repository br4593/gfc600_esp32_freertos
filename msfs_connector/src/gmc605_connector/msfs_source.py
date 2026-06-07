from __future__ import annotations

import logging
import math
from typing import Any

from .model import (
    AircraftData,
    Command,
    CommandResult,
    Deviation,
    PanelSnapshot,
    References,
    normalize_heading,
    to_bool,
    to_int,
)
from .source import SnapshotSource

LOGGER = logging.getLogger(__name__)


class MsfsSource(SnapshotSource):
    name = "msfs"

    def __init__(self, cache_ms: int = 100) -> None:
        self._cache_ms = cache_ms
        self._simconnect: Any = None
        # name -> SimConnect Request, built explicitly from _SIMVAR_DEFS so the
        # set of variables does not depend on the bundled library's (stale)
        # AircraftRequests list.
        self._requests: dict[str, Any] = {}
        # event name -> mapped SimConnect event id (lazy cache)
        self._events: dict[str, Any] = {}
        self._last_snapshot = PanelSnapshot(source=self.name)
        self._last_approach_selected = False

    def open(self) -> None:
        try:
            from SimConnect import Request, SimConnect
        except ImportError as exc:
            raise RuntimeError(
                "Python-SimConnect is required for MSFS mode; "
                'install with: python -m pip install -e ".[msfs]"'
            ) from exc

        self._simconnect = SimConnect()
        # Define each SimVar directly. This bypasses AircraftRequests, whose
        # dictionary is missing several modern MSFS autopilot variables.
        # An unknown name in that list silently reads as None, so keep the
        # requested set explicit and review every mapped variable against the SDK.
        self._requests = {
            name: Request(
                (simvar, unit),
                self._simconnect,
                _time=self._cache_ms,
                _settable=settable,
            )
            for name, (simvar, unit, settable) in _SIMVAR_DEFS.items()
        }
        self._events = {}
        self._last_snapshot = PanelSnapshot(source=self.name)
        self._last_approach_selected = False

    def close(self) -> None:
        if self._simconnect is not None:
            self._simconnect.exit()
        self._simconnect = None
        self._requests = {}
        self._events = {}
        self._last_approach_selected = False

    def poll(self) -> PanelSnapshot:
        if self._simconnect is None:
            raise RuntimeError("MSFS source is not open")

        values = {name: self._get(name) for name in _SIMVAR_DEFS}
        snapshot = derive_snapshot(values)
        self._last_snapshot = snapshot
        self._last_approach_selected = any(
            to_bool(values.get(name))
            for name in ("AUTOPILOT_APPROACH_HOLD", "AUTOPILOT_APPROACH_CAPTURED")
        )
        return snapshot

    def handle_command(self, command: Command) -> CommandResult:
        if self._simconnect is None:
            return self._result(command, False, "MSFS source is not open")

        try:
            event_name, value = self._map_command(command)
        except ValueError as exc:
            return self._result(command, False, str(exc))
        if event_name is None:
            return self._result(
                command,
                False,
                "no reliable generic MSFS event; aircraft adapter required",
            )

        try:
            sent = self._transmit(event_name, 0 if value is None else int(value))
        except Exception as exc:  # third-party SimConnect wrapper exceptions vary
            LOGGER.exception("failed to transmit MSFS event %s", event_name)
            return self._result(command, False, str(exc))

        if not sent:
            return self._result(command, False, f"event not sent: {event_name}")
        return self._result(command, True, f"transmitted {event_name}")

    def _transmit(self, event_name: str, value: int) -> bool:
        """Map and transmit any MSFS key event to the user aircraft.

        Uses SimConnect.map_to_sim_event so the connector can drive MSFS with
        event IDs that are not in the bundled library's AircraftEvents list.
        """
        from SimConnect import DWORD

        sm = self._simconnect
        mapped = self._events.get(event_name)
        if mapped is None:
            mapped = sm.map_to_sim_event(event_name.encode("ascii"))
            if mapped is None:
                return False
            self._events[event_name] = mapped
        return bool(sm.send_event(mapped, DWORD(value)))

    def _get(self, name: str) -> Any:
        request = self._requests.get(name)
        if request is None:
            return None
        try:
            return request.value
        except Exception:
            LOGGER.debug("failed to read SimVar %s", name, exc_info=True)
            return None

    def _result(
        self, command: Command, accepted: bool, message: str
    ) -> CommandResult:
        return CommandResult(
            command_seq=command.seq,
            command=command.command,
            accepted=accepted,
            message=message,
        )

    def _map_command(self, command: Command) -> tuple[str | None, int | None]:
        name = command.command
        snapshot = self._last_snapshot

        if name == "AP_PRESS":
            return "AP_MASTER", None
        if name == "FD_PRESS":
            return "TOGGLE_FLIGHT_DIRECTOR", None
        if name == "YD_PRESS":
            return "YAW_DAMPER_TOGGLE", None
        if name == "AP_DISCONNECT":
            return "AUTOPILOT_DISENGAGE_SET", 1

        if name == "HDG_PRESS":
            return (
                "AP_HDG_HOLD_OFF" if snapshot.lat_active == "HDG" else "AP_HDG_HOLD_ON",
                None,
            )
        if name == "NAV_PRESS":
            active = (
                snapshot.lat_active in {"GPS", "VOR", "LOC"}
                and not self._last_approach_selected
            )
            return "AP_NAV1_HOLD_OFF" if active else "AP_NAV1_HOLD_ON", None
        if name == "APR_PRESS":
            return (
                "AP_APR_HOLD_OFF" if self._last_approach_selected else "AP_APR_HOLD_ON",
                None,
            )
        if name == "BC_PRESS":
            return (
                "AP_BC_HOLD_OFF" if snapshot.lat_active == "BC" else "AP_BC_HOLD_ON",
                None,
            )

        vertical_events = {
            "ALT_PRESS": ("ALT", "AP_ALT_HOLD_ON", "AP_ALT_HOLD_OFF"),
            "VS_PRESS": ("VS", "AP_VS_ON", "AP_VS_OFF"),
            "IAS_PRESS": ("IAS", "AP_AIRSPEED_ON", "AP_AIRSPEED_OFF"),
            "FLC_PRESS": ("FLC", "FLIGHT_LEVEL_CHANGE_ON", "FLIGHT_LEVEL_CHANGE_OFF"),
        }
        if name in vertical_events:
            mode, on_event, off_event = vertical_events[name]
            return (off_event if snapshot.vert_active == mode else on_event), None

        reference_events = {
            "HEADING_SET": "HEADING_BUG_SET",
            "ALTITUDE_SET": "AP_ALT_VAR_SET_ENGLISH",
            "VS_SET": "AP_VS_VAR_SET_ENGLISH",
            # AP_SPD_VAR_SET takes the reference directly in knots. (The EX1
            # variant divides the parameter by 100, so a 250 kt bug sent as
            # 250 would set 2.5 kt.)
            "SPEED_SET": "AP_SPD_VAR_SET",
        }
        if name in reference_events:
            value = _command_int(command.value, name)
            if name == "HEADING_SET":
                value = normalize_heading(value)
            if name == "SPEED_SET":
                value = max(0, value)
            return reference_events[name], value

        return None, None


# Explicit SimConnect variable definitions: key -> (SimVar name, unit, settable).
# Units are chosen so derive_snapshot can consume the raw value as-is. In
# particular PLANE HEADING DEGREES MAGNETIC is requested in Degrees: its native
# unit is radians, and requesting it as radians (the bundled library's default)
# would make normalize_heading() return 0-6 instead of 0-360.
# Verified against the MSFS SDK "Aircraft Autopilot/Assistant Variables" page.
_SIMVAR_DEFS: dict[str, tuple[bytes, bytes, bool]] = {
    "AUTOPILOT_MASTER": (b"AUTOPILOT MASTER", b"Bool", False),
    "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": (
        b"AUTOPILOT FLIGHT DIRECTOR ACTIVE", b"Bool", False),
    "AUTOPILOT_YAW_DAMPER": (b"AUTOPILOT YAW DAMPER", b"Bool", False),
    "AUTOPILOT_HEADING_LOCK": (b"AUTOPILOT HEADING LOCK", b"Bool", False),
    "AUTOPILOT_NAV1_LOCK": (b"AUTOPILOT NAV1 LOCK", b"Bool", False),
    "AUTOPILOT_APPROACH_HOLD": (b"AUTOPILOT APPROACH HOLD", b"Bool", False),
    "AUTOPILOT_APPROACH_CAPTURED": (
        b"AUTOPILOT APPROACH CAPTURED", b"Bool", False),
    "AUTOPILOT_BACKCOURSE_HOLD": (b"AUTOPILOT BACKCOURSE HOLD", b"Bool", False),
    "AUTOPILOT_APPROACH_IS_LOCALIZER": (
        b"AUTOPILOT APPROACH IS LOCALIZER", b"Bool", False),
    "AUTOPILOT_ALTITUDE_LOCK": (b"AUTOPILOT ALTITUDE LOCK", b"Bool", False),
    "AUTOPILOT_ALTITUDE_ARM": (b"AUTOPILOT ALTITUDE ARM", b"Bool", False),
    "AUTOPILOT_VERTICAL_HOLD": (b"AUTOPILOT VERTICAL HOLD", b"Bool", False),
    "AUTOPILOT_AIRSPEED_HOLD": (b"AUTOPILOT AIRSPEED HOLD", b"Bool", False),
    "AUTOPILOT_FLIGHT_LEVEL_CHANGE": (
        b"AUTOPILOT FLIGHT LEVEL CHANGE", b"Bool", False),
    "AUTOPILOT_GLIDESLOPE_HOLD": (b"AUTOPILOT GLIDESLOPE HOLD", b"Bool", False),
    "AUTOPILOT_GLIDESLOPE_ACTIVE": (
        b"AUTOPILOT GLIDESLOPE ACTIVE", b"Bool", False),
    "GPS_DRIVES_NAV1": (b"GPS DRIVES NAV1", b"Bool", False),
    "HSI_HAS_LOCALIZER": (b"HSI HAS LOCALIZER", b"Bool", False),
    "HSI_CDI_NEEDLE": (b"HSI CDI NEEDLE", b"Number", False),
    "HSI_CDI_NEEDLE_VALID": (b"HSI CDI NEEDLE VALID", b"Bool", False),
    "HSI_GSI_NEEDLE": (b"HSI GSI NEEDLE", b"Number", False),
    "HSI_GSI_NEEDLE_VALID": (b"HSI GSI NEEDLE VALID", b"Bool", False),
    "AUTOPILOT_HEADING_LOCK_DIR": (
        b"AUTOPILOT HEADING LOCK DIR", b"Degrees", False),
    "AUTOPILOT_ALTITUDE_LOCK_VAR": (
        b"AUTOPILOT ALTITUDE LOCK VAR", b"Feet", False),
    "AUTOPILOT_VERTICAL_HOLD_VAR": (
        b"AUTOPILOT VERTICAL HOLD VAR", b"Feet/minute", False),
    "AUTOPILOT_AIRSPEED_HOLD_VAR": (
        b"AUTOPILOT AIRSPEED HOLD VAR", b"Knots", False),
    "PLANE_HEADING_DEGREES_MAGNETIC": (
        b"PLANE HEADING DEGREES MAGNETIC", b"Degrees", False),
    "INDICATED_ALTITUDE": (b"INDICATED ALTITUDE", b"Feet", False),
    "VERTICAL_SPEED": (b"VERTICAL SPEED", b"Feet/minute", False),
    "AIRSPEED_INDICATED": (b"AIRSPEED INDICATED", b"Knots", False),
}

# Backwards-compatible tuple of variable keys.
SIMVARS = tuple(_SIMVAR_DEFS)


def derive_snapshot(values: dict[str, Any]) -> PanelSnapshot:
    ap = to_bool(values.get("AUTOPILOT_MASTER"))
    fd = to_bool(values.get("AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE")) or ap
    yd = to_bool(values.get("AUTOPILOT_YAW_DAMPER"))

    cdi = Deviation.from_needle(
        to_bool(values.get("HSI_CDI_NEEDLE_VALID")),
        values.get("HSI_CDI_NEEDLE"),
    )
    gsi = Deviation.from_needle(
        to_bool(values.get("HSI_GSI_NEEDLE_VALID")),
        _normalize_gsi_needle(values.get("HSI_GSI_NEEDLE")),
    )
    nav_source = derive_nav_source(values, cdi.valid)
    if any(
        to_bool(values.get(name))
        for name in ("AUTOPILOT_APPROACH_HOLD", "AUTOPILOT_APPROACH_CAPTURED")
    ) and to_bool(values.get("AUTOPILOT_APPROACH_IS_LOCALIZER")):
        nav_source = "LOC"

    lat_active = derive_lateral_active(values, fd, nav_source)
    lat_armed = derive_lateral_armed(values, nav_source)
    vert_active = derive_vertical_active(values, fd, nav_source)
    vert_armed = derive_vertical_armed(values, nav_source, vert_active)

    return PanelSnapshot(
        source="msfs",
        sim_connected=True,
        ap=ap,
        fd=fd,
        yd=yd,
        lat_active=lat_active,
        lat_armed=lat_armed,
        vert_active=vert_active,
        vert_armed=vert_armed,
        nav_source=nav_source,
        cdi=cdi,
        gsi=gsi,
        references=References(
            heading_deg=normalize_heading(values.get("AUTOPILOT_HEADING_LOCK_DIR")),
            altitude_ft=to_int(values.get("AUTOPILOT_ALTITUDE_LOCK_VAR")),
            vs_fpm=to_int(values.get("AUTOPILOT_VERTICAL_HOLD_VAR")),
            speed_kt=to_int(values.get("AUTOPILOT_AIRSPEED_HOLD_VAR")),
        ),
        aircraft=AircraftData(
            heading_deg=normalize_heading(values.get("PLANE_HEADING_DEGREES_MAGNETIC")),
            altitude_ft=to_int(values.get("INDICATED_ALTITUDE")),
            vs_fpm=to_int(values.get("VERTICAL_SPEED")),
            airspeed_kt=to_int(values.get("AIRSPEED_INDICATED")),
        ),
    )


def derive_nav_source(values: dict[str, Any], cdi_valid: bool) -> str:
    if to_bool(values.get("GPS_DRIVES_NAV1")):
        return "GPS"
    if to_bool(values.get("HSI_HAS_LOCALIZER")):
        return "LOC"
    if cdi_valid:
        return "VOR"
    return "NONE"


def semantic_lateral(nav_source: str, approach: bool) -> str:
    if nav_source == "NONE":
        return "NONE"
    if approach and nav_source == "VOR":
        return "VAPP"
    return nav_source


def derive_lateral_active(
    values: dict[str, Any], fd: bool, nav_source: str
) -> str:
    if not fd:
        return "NONE"
    if to_bool(values.get("AUTOPILOT_BACKCOURSE_HOLD")):
        return "BC"
    if any(
        to_bool(values.get(name))
        for name in (
            "AUTOPILOT_APPROACH_CAPTURED",
            "AUTOPILOT_APPROACH_HOLD",
        )
    ):
        if to_bool(values.get("AUTOPILOT_APPROACH_IS_LOCALIZER")):
            return "LOC"
        return semantic_lateral(nav_source, approach=True)
    if to_bool(values.get("AUTOPILOT_NAV1_LOCK")):
        return semantic_lateral(nav_source, approach=False)
    if to_bool(values.get("AUTOPILOT_HEADING_LOCK")):
        return "HDG"
    return "ROL"


def derive_lateral_armed(values: dict[str, Any], nav_source: str) -> str:
    # Generic MSFS SimVars do not expose a reliable NAV/APR armed state.
    # AUTOPILOT APPROACH ARM is documented as approach-flight-plan activity,
    # not the panel's selected/armed lateral mode.
    return "NONE"


def derive_vertical_active(
    values: dict[str, Any], fd: bool, nav_source: str
) -> str:
    if not fd:
        return "NONE"
    if nav_source == "LOC" and any(
        to_bool(values.get(name))
        for name in ("AUTOPILOT_GLIDESLOPE_ACTIVE", "AUTOPILOT_GLIDESLOPE_HOLD")
    ):
        return "GS"
    if to_bool(values.get("AUTOPILOT_ALTITUDE_LOCK")):
        return "ALT"
    if to_bool(values.get("AUTOPILOT_FLIGHT_LEVEL_CHANGE")):
        return "FLC"
    if to_bool(values.get("AUTOPILOT_AIRSPEED_HOLD")):
        return "IAS"
    if to_bool(values.get("AUTOPILOT_VERTICAL_HOLD")):
        return "VS"
    return "PIT"


def derive_vertical_armed(
    values: dict[str, Any], nav_source: str, vert_active: str
) -> list[str]:
    armed: list[str] = []
    if to_bool(values.get("AUTOPILOT_ALTITUDE_ARM")) and vert_active != "ALT":
        armed.append("ALTS")
    # AUTOPILOT GLIDESLOPE ARM is documented as active-on-glideslope and
    # therefore cannot safely drive a distinct armed annunciation.
    return armed


def _command_int(value: object, command_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{command_name} value must be a number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{command_name} value must be finite")
    return int(round(float(value)))


def _normalize_gsi_needle(value: object) -> float | None:
    if value is None:
        return None
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(raw):
        return None
    return raw * 127.0 / 119.0
