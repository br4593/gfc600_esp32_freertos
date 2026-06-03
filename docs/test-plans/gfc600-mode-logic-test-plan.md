# GFC 600-Style Mode Logic Test Plan

Purpose: validate the ESP32/MSFS annunciation model against expected GFC 600-style behavior.

Primary source: Garmin `GFC 600 Automatic Flight Control System (with Color Display) Pilot's Guide`, `190-03090-00 Rev. A`, January 2024.

Simulator boundary: tests verify a simulator panel and display model only.

## Test Setup

Record for every test:

- MSFS aircraft.
- Autopilot implementation used by that aircraft.
- Nav source: GPS, VOR, LOC.
- Selected altitude.
- Current altitude.
- CDI/VDEV if available.
- Button pressed.
- Expected OLED labels.
- Actual OLED labels.
- MSFS AP behavior.

## Core Display Tests

| Test | Action | Expected Display |
|---|---|---|
| Power/PFT | Start panel state machine | `PFT`, then normal ready state. |
| FD on | Press `FD` with FD off | active lateral `ROL`, active vertical `PIT`, `ALTS` armed if configured. |
| AP on from FD off | Press `AP` | `AP` on, active `ROL`/`PIT`. |
| AP on from FD on | Press `AP` after selecting modes | `AP` on, previous active FD modes preserved. |
| AP manual disconnect | Press AP disconnect | `AP` flashes attention state for about 5 sec, then off. |
| YD engagement | Press `YD` if configured | `YD` displayed steady active. |

## Vertical Mode Tests

| Test | Setup | Action | Expected Display |
|---|---|---|---|
| Pitch default | FD/AP off | Press `FD` or `AP` | `PIT` active. |
| Pitch wheel | `PIT` active | NOSE UP/DN | pitch reference changes by 0.5 deg per click. |
| VS select | Stable flight | Press `VS` | `VS` active, VS ref shown, `ALTS` armed if configured. |
| VS wheel | `VS` active | NOSE UP/DN | VS ref changes by 100 fpm per click. |
| IAS select | Stable flight | Press `IAS` | `IAS` active, airspeed ref shown, `ALTS` armed if configured. |
| FLC select | Stable flight | Press `FLC` | `FLC` active, airspeed ref shown, `ALTS` armed if configured. |
| ALT select | Any stable altitude | Press `ALT` | `ALT` active, altitude ref nearest 10 ft. |
| ALTS capture | Climb/descent toward selected altitude | Let aircraft approach selected altitude | `ALTS` active/capture attention, `ALT` armed. |
| ALT final capture | Within about 50 ft of selected altitude | Continue | `ALT` active. |
| GP arm | GPS approach loaded, GPS source | Press `APR` | lateral `GPS` armed/active, vertical `GP` armed. |
| GP capture | Intercept glidepath | Continue inbound | `GP` active. |
| GS arm | ILS loaded, LOC source valid | Press `APR` | lateral `LOC` armed/active, vertical `GS` armed. |
| GS capture | Intercept glideslope | Continue inbound | `GS` active. |
| LVL | Any mode | Press `LVL` | `LVL` active in lateral and vertical, armed modes cleared. |
| GA | Any airborne mode | Press `GA` | `GA` active in lateral and vertical, `ALTS` armed if configured. |

## Lateral Mode Tests

| Test | Setup | Action | Expected Display |
|---|---|---|---|
| Roll default wings level | Bank less than 6 deg | Activate FD/AP | `ROL`, command wings level. |
| Roll hold | Bank 6 to 25 deg | Activate FD/AP | `ROL`, hold bank reference. |
| Roll limit | Bank more than 25 deg | Activate FD/AP | `ROL`, limit bank command to 25 deg. |
| HDG | Heading bug set | Press `HDG` | `HDG` active. |
| GPS NAV arm | GPS source, CDI more than half scale | Press `NAV` | previous lateral active, `GPS` armed. |
| GPS NAV capture | Course intercept | Continue | `GPS` active. |
| VOR NAV arm | VOR source, CDI more than half scale | Press `NAV` | previous lateral active, `VOR` armed. |
| LOC NAV capture | LOC source, CDI less than half scale | Press `NAV` | `LOC` active. |
| GPS APR | GPS approach loaded | Press `APR` | `GPS` approach active/armed; `GP` armed if vertical guidance exists. |
| VOR APR | VOR approach | Press `APR` | `VAPP` on GMC-style display, or `VOR` on GI 285-style display. |
| LOC APR | ILS/LOC approach | Press `APR` | `LOC` lateral, `GS` armed if glideslope exists. |
| BC | Localizer backcourse scenario | Press `BC` | `BC` active/armed depending capture. |
| Source change reversion | NAV/APR active, autoswitch disabled | Change nav source | Revert lateral active to `ROL`. |

## VNAV Tests

Treat as phase-2 unless the selected MSFS aircraft exposes enough VNAV state.

| Test | Setup | Action | Expected Display |
|---|---|---|---|
| VNAV arm | GPS flight plan with constraints | Press `VNV` | `VPTH` armed. |
| VNAV capture | Reach TOD/path | Continue | `VPTH` active. |
| Constraint capture | VNAV descent to constraint | Continue | `ALTV` active or armed. |
| VNAV to GPS approach | VNAV active, GPS APR armed | Intercept glidepath | transition to `GP`. |
| VNAV to ILS | VNAV active, LOC/GS armed | Intercept localizer/glideslope | transition to `LOC`/`GS`. |

## Pass Criteria

- Active lateral and vertical labels match expected mode state.
- Armed labels appear only when a mode is selected but not captured.
- Coupled modes `LVL` and `GA` replace both lateral and vertical active labels.
- References update with the expected step size.
- Flash/attention states expire and do not leave stale labels.
- Local Garmin-style display state remains stable even when MSFS lacks a perfect matching mode.

