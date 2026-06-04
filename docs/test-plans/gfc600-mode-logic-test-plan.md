# GFC 600 Mode Logic Test Plan

Purpose: validate the ESP32/MSFS annunciation model against expected GFC 600-style behavior.

Primary source: Garmin `GFC 600 Automatic Flight Control System (with Color Display) Pilot's Guide`, `190-03090-00 Rev. A`, January 2024.

Simulator boundary: tests verify a simulator panel and display model only.

Expected transitions are defined in
[GFC 600 Mode Logic](../state-machines/gfc600-mode-logic.md).

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
| Invalid AP/FD combination | Force or receive AP on with FD off | State manager corrects to FD on or rejects the update. |

## Mode-Key Activation Tests

| Test | Setup | Action | Expected Display / State |
|---|---|---|---|
| HDG activates FD | FD off, AP off | Press `HDG` | FD on, AP off, `HDG` active, `PIT` active. |
| VS activates FD | FD off, AP off | Press `VS` | FD on, AP off, `ROL` active, `VS` active. |
| ALT activates FD | FD off, AP off | Press `ALT` | FD on, AP off, `ROL` active, `ALT` active. |
| Valid GPS NAV activates FD | FD off, AP off, valid GPS course | Press `NAV` | FD on, AP off, `GPS` active or armed, `PIT` active. |
| Invalid NAV does not activate FD | FD off, AP off, no valid nav source | Press `NAV` | No state change; diagnostic recorded. |
| LVL engages AP | FD off, AP off | Press `LVL` | FD on, AP on, `LVL` active on both axes. |
| GA does not engage AP | FD off, AP off | Press `GA` | FD on, AP off, `GA` active on both axes. |
| Active HDG deselection | FD on, AP off, `HDG` active | Press `HDG` | `ROL` active, AP remains off. |
| Armed GPS NAV deselection | `HDG` active, `GPS_NAV` armed | Press `NAV` | `HDG` remains active, GPS armed indication removed. |
| Active GPS NAV deselection | `GPS_NAV` active | Press `NAV` | `ROL` active. |
| Armed GPS APR deselection | `HDG` active, `GPS_APR` and `GP` armed | Press `APR` | `HDG` remains active, GPS and `GP` armed indications removed. |
| Active GPS APR deselection | `GPS_APR` active, `GP` armed or active | Press `APR` | Lateral reverts to `ROL`; `GP` is removed and vertical reverts to `PIT` if `GP` was active. |
| FD key disabled with AP | FD on, AP on | Press `FD` | No state change. |

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
| Multiple vertical arms | `VPTH` active on a GPS approach, descending toward a constraint | Arm approach and continue descent | `ALTV` and `GP` are both armed while `VPTH` remains active. |
| VNV deselection while armed | `VPTH` armed | Press `VNV` | Current active vertical mode remains; `VPTH` and `ALTV` are removed. |
| VNV deselection while active | `VPTH` active | Press `VNV` | Vertical reverts to `PIT`; VNAV armed modes are removed. |
| Selected altitude changed during capture | `ALTS` active | Change selected altitude | `PIT` active and `ALTS` armed for the new target. |
| LVL | Any mode | Press `LVL` | `LVL` active in lateral and vertical, armed modes cleared. |
| GA | Any airborne mode | Press `GA` | `GA` active in lateral and vertical, `ALTS` armed if configured. |
| GA attitude modification | `GA` active | Use CWS or NOSE UP/DN wheel | Lateral `ROL`, vertical `PIT`, and `ALTS` armed if configured. |

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
| GPS NAV to APR semantic conversion | `GPS_NAV` active or armed | Press `APR` | Visible `GPS` remains, internal owner becomes `GPS_APR`, and `GP` arms. |
| GPS APR to NAV semantic conversion | `GPS_APR` active or armed, `GP` armed | Press `NAV` | Visible `GPS` remains, internal owner becomes `GPS_NAV`, and `GP` cancels. |
| LOC NAV to APR semantic conversion | `LOC_NAV` active or armed | Press `APR` | Visible `LOC` remains, internal owner becomes `LOC_APR`, and `GS` arms. |
| LOC APR to NAV semantic conversion | `LOC_APR` active or armed, `GS` armed | Press `NAV` | Visible `LOC` remains, internal owner becomes `LOC_NAV`, and `GS` cancels. |
| LOC capture inhibit | `LOC_APR` armed, heading differs from course by more than 105 deg | Intercept localizer signal | `LOC_APR` remains armed and does not capture. |
| DG cannot arm | DG profile, valid source, CDI more than half scale | Press `NAV`, `APR`, or `BC` | No armed lateral mode is entered. |
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

## Automatic Reversion And Protection Tests

| Test | Setup | Action | Expected Display / State |
|---|---|---|---|
| Active lateral data invalid | NAV/APR active | Invalidate required navigation data | Lateral reverts to wings-level `ROL`; dropped mode flashes yellow. |
| Active vertical data invalid | Air-data-dependent vertical mode active | Invalidate required mode data | Vertical reverts to `PIT`; dropped mode flashes yellow. |
| Default-mode attitude invalid | FD active | Invalidate required attitude data | FD disables and active/armed mode annunciations clear. |
| Overspeed enter and restore | `VS` active | Trigger and then clear overspeed | `MAXSPEED`; `IAS`/`FLC` active; `VS` shown armed, then restored active when clear. |
| Altitude-critical underspeed | `GP` active with AP on | Trigger and then clear underspeed | `MINSPEED`; `ROL` and `IAS`/`FLC` active; prior lateral and `GP` shown armed, then restored. |
| Non-altitude-critical underspeed | `VS` active with AP on | Trigger and then clear underspeed | `MINSPEED`; lateral unchanged; `IAS`/`FLC` active; `VS` shown armed, then restored. |

## Pass Criteria

- Active lateral and vertical labels match expected mode state.
- Internal NAV/APR ownership is correct even when the visible `GPS` or `LOC`
  label does not change.
- All compatible armed vertical labels appear; one armed mode must not erase
  another.
- Protection restore targets are kept separate from normal capture-armed modes.
- Coupled modes `LVL` and `GA` replace both lateral and vertical active labels.
- References update with the expected step size.
- Flash/attention states expire and do not leave stale labels.
- Local Garmin-style display state remains stable even when MSFS lacks a perfect matching mode.

