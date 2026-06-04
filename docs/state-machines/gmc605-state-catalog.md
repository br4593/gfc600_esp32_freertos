# GMC 605-Style Firmware State Catalog

## Goal

Provide one implementation-oriented list of the states used by the GMC 605-style
ESP32 panel.

This project is for Microsoft Flight Simulator only. These states describe a
simulator control panel and display model, not real aircraft autopilot control
logic.

## Sources Used

- Garmin, `GFC 600 Automatic Flight Control System (with Color Display) Pilot's
  Guide`, `190-03090-00 Rev. A`, January 2024:
  https://static.garmin.com/pumac/190-03090-00_a.pdf
- [GFC 600-Style Mode State Machines](gfc600-mode-state-machines.md)
- [GFC 600-Style Display Annunciation Workflow](../workflows/gfc600-display-annunciation-workflow.md)
- [GFC 600 Operation Logic Research Summary](../research/gfc600-operation-logic.md)

## Modeling Rules

The firmware should not use one large enum for the whole system. The panel has
several independent state groups that exist at the same time.

For example:

- The autopilot can be off while the flight director is on.
- `HDG` can be active while `GPS` is armed.
- `VS` can be active while `ALTS` is armed.
- `LVL` and `GA` are coupled modes that set both lateral and vertical state.

Only the state manager should modify the writable state instance. Buttons, the
MSFS link, and timers should send events to the state manager.

## System Lifecycle States

These describe the panel firmware lifecycle, not a flight director mode.

| State | Meaning | Display Behavior |
|---|---|---|
| `SYSTEM_BOOT` | ESP32 firmware is starting and initializing services. | Serial diagnostics; display may be blank. |
| `SYSTEM_PFT` | Preflight test is in progress. | Show `PFT` when a display is available. |
| `SYSTEM_READY` | Panel is initialized and available for normal operation. | Normal annunciation display. |
| `SYSTEM_FAIL` | A required simulated panel self-test or initialization step failed. | Show `PFT FAIL` or a specific failure message. |

`POWER_OFF` is useful in diagrams, but it is normally not a firmware runtime
state because the ESP32 cannot execute while unpowered.

## Flight Director States

| State | Meaning |
|---|---|
| `FD_OFF` | Flight director is not active. |
| `FD_ON` | Flight director is active. |

When FD is first enabled without an existing active mode selection, the default
mode combination is:

- Active lateral: `ROL`
- Active vertical: `PIT`
- Armed vertical: `ALTS` if selected-altitude capture is available

## Autopilot States

| State | Meaning | Display Behavior |
|---|---|---|
| `AP_OFF` | Autopilot servos are not engaged. | Do not show steady `AP`. |
| `AP_ON` | Autopilot is engaged and following the flight director. | Show steady `AP`. |
| `AP_MANUAL_DISCONNECT` | A manual disconnect alert is active. | Flash `AP` for the configured alert duration. |
| `AP_AUTOMATIC_DISCONNECT` | An abnormal or automatic disconnect alert is active. | Flash failure-priority `AP` until acknowledged. |
| `AP_FAIL` | A simulated autopilot failure is active. | Show failure-priority `AP` indication. |

The AP state is separate from FD state. Pressing AP while FD is off should also
enable FD and establish the default `PIT` and `ROL` modes.

## Yaw Damper States

| State | Meaning | Display Behavior |
|---|---|---|
| `YD_OFF` | Yaw damper is not engaged. | Do not show steady `YD`. |
| `YD_ON` | Yaw damper is engaged. | Show steady `YD`. |
| `YD_MANUAL_DISCONNECT` | A manual yaw damper disconnect alert is active. | Flash `YD`. |
| `YD_FAIL` | A simulated yaw damper failure is active. | Show failure-priority `YD` indication. |

Yaw damper behavior is installation-dependent and should be configurable.

## Active Lateral Mode States

Exactly one active lateral mode should be selected while the flight director is
active.

| State | Display Label | Meaning |
|---|---|---|
| `LAT_ACTIVE_NONE` | none | No active lateral mode, normally used while FD is off or during initialization. |
| `LAT_ACTIVE_ROL` | `ROL` | Roll Hold mode. Default lateral mode. |
| `LAT_ACTIVE_HDG` | `HDG` | Heading Select mode. |
| `LAT_ACTIVE_GPS` | `GPS` | GPS navigation or GPS approach tracking. |
| `LAT_ACTIVE_VOR` | `VOR` | VOR navigation tracking. |
| `LAT_ACTIVE_VAPP` | `VAPP` | VOR approach tracking on the GMC-style display. |
| `LAT_ACTIVE_LOC` | `LOC` | Localizer navigation or approach tracking. |
| `LAT_ACTIVE_BC` | `BC` | Localizer backcourse tracking. |
| `LAT_ACTIVE_LVL` | `LVL` | Level mode lateral command. |
| `LAT_ACTIVE_GA` | `GA` | Go Around lateral command. |

## Armed Lateral Mode States

Exactly zero or one lateral mode should be armed.

| State | Display Label | Meaning |
|---|---|---|
| `LAT_ARMED_NONE` | none | No lateral mode is waiting for capture. |
| `LAT_ARMED_GPS` | `GPS` | GPS course is selected but not yet captured. |
| `LAT_ARMED_VOR` | `VOR` | VOR course is selected but not yet captured. |
| `LAT_ARMED_VAPP` | `VAPP` | VOR approach is selected but not yet captured. |
| `LAT_ARMED_LOC` | `LOC` | Localizer course is selected but not yet captured. |
| `LAT_ARMED_BC` | `BC` | Backcourse is selected but not yet captured. |

The button name `NAV` is an event or selection request, not a lateral mode
state. The resulting armed or active state depends on the selected navigation
source.

## Active Vertical Mode States

Exactly one active vertical mode should be selected while the flight director is
active.

| State | Display Label | Meaning |
|---|---|---|
| `VERT_ACTIVE_NONE` | none | No active vertical mode, normally used while FD is off or during initialization. |
| `VERT_ACTIVE_PIT` | `PIT` | Pitch Hold mode. Default vertical mode. |
| `VERT_ACTIVE_ALT` | `ALT` | Altitude Hold mode. |
| `VERT_ACTIVE_ALTS` | `ALTS` | Selected altitude capture is active. |
| `VERT_ACTIVE_VS` | `VS` | Vertical Speed mode. |
| `VERT_ACTIVE_IAS` | `IAS` | Indicated Airspeed mode on the IAS-key panel variant. |
| `VERT_ACTIVE_FLC` | `FLC` | Flight Level Change mode on the FLC-key panel variant. |
| `VERT_ACTIVE_VPTH` | `VPTH` | VNAV vertical path tracking. |
| `VERT_ACTIVE_ALTV` | `ALTV` | VNAV constraint altitude capture. |
| `VERT_ACTIVE_GP` | `GP` | GPS glidepath tracking. |
| `VERT_ACTIVE_GS` | `GS` | ILS glideslope tracking. |
| `VERT_ACTIVE_LVL` | `LVL` | Level mode vertical command. |
| `VERT_ACTIVE_GA` | `GA` | Go Around vertical command. |

The selected panel profile should decide whether the user-facing speed mode is
`IAS` or `FLC`. Keeping both states in the catalog allows different profiles
without changing the core state model.

## Armed Vertical Mode States

Exactly zero or one primary vertical mode should be armed in the first firmware
version. More advanced installations may require multiple simultaneous armed
vertical indications later.

| State | Display Label | Meaning |
|---|---|---|
| `VERT_ARMED_NONE` | none | No vertical mode is waiting for capture. |
| `VERT_ARMED_ALTS` | `ALTS` | Selected altitude capture is armed. |
| `VERT_ARMED_ALT` | `ALT` | Altitude Hold is armed after selected-altitude capture begins. |
| `VERT_ARMED_VPTH` | `VPTH` | VNAV vertical path is armed. |
| `VERT_ARMED_ALTV` | `ALTV` | VNAV constraint altitude capture is armed, if required by the selected profile. |
| `VERT_ARMED_GP` | `GP` | GPS glidepath capture is armed. |
| `VERT_ARMED_GS` | `GS` | ILS glideslope capture is armed. |

## Coupled Mode Rules

`LVL` and `GA` affect both axes and should be applied as coordinated state
transitions.

| Coupled Mode | Active Lateral | Active Vertical | Typical Armed Vertical |
|---|---|---|---|
| Level Mode | `LAT_ACTIVE_LVL` | `VERT_ACTIVE_LVL` | `VERT_ARMED_NONE` |
| Go Around | `LAT_ACTIVE_GA` | `VERT_ACTIVE_GA` | `VERT_ARMED_ALTS` if selected-altitude capture is available |

## Navigation Source States

Navigation source is not an autopilot mode, but it is required to decide what
`NAV` and `APR` events mean.

| State | Meaning |
|---|---|
| `NAV_SOURCE_NONE` | No usable navigation source is selected. |
| `NAV_SOURCE_GPS` | GPS/FMS navigation source is selected. |
| `NAV_SOURCE_VOR` | VOR navigation source is selected. |
| `NAV_SOURCE_LOC` | Localizer-capable navigation source is selected. |

Additional data is needed to distinguish normal navigation from an approach,
such as approach validity, backcourse selection, CDI deviation, and signal
validity.

## Guidance Modifier States

These states modify how a normal mode behaves without replacing the active
lateral or vertical mode.

| State | Display Label | Meaning |
|---|---|---|
| `TRACK_MODE_OFF` | none | Normal heading information is available. |
| `TRACK_MODE_ACTIVE` | `TRACK MODE` | Reversionary GPS track behavior is active because heading information is unavailable in a supported installation. |
| `SMART_GLIDE_OFF` | none | Smart Glide is not affecting the IAS reference. |
| `SMART_GLIDE_ACTIVE` | `GLIDE` | Smart Glide is active and IAS mode initially targets Best Glide Speed. |
| `LOW_BANK_OFF` | none | Normal configured bank limits are used. |
| `LOW_BANK_ON` | profile-dependent | Reduced bank limits are active. |

`TRACK MODE` should be modeled as a modifier unless later MSFS testing shows a
clear reason to treat it as a separate lateral mode.

## Control Wheel Steering States

Control Wheel Steering is a held control condition, not a lateral or vertical
mode.

| State | Meaning |
|---|---|
| `CWS_RELEASED` | Normal autopilot servo behavior. |
| `CWS_HELD` | CWS is being held; the host adapter may temporarily release or synchronize simulated guidance. |

## Emergency Descent Mode States

Emergency Descent Mode is optional and installation-dependent. It coordinates
multiple modes and references instead of replacing the lateral and vertical mode
enums.

| State | Display Label | Meaning |
|---|---|---|
| `EDM_OFF` | none | Emergency Descent Mode is not armed or active. |
| `EDM_ARMED` | profile-dependent | EDM arming conditions are satisfied. |
| `EDM_DELAY` | profile-dependent | EDM has been triggered and the activation delay timer is running. |
| `EDM_ACTIVE` | `EDM` | EDM is controlling the configured descent behavior. |
| `EDM_INHIBITED` | profile-dependent | Automatic activation is temporarily inhibited. |
| `EDM_OVERRIDDEN` | profile-dependent | EDM has been overridden until its arming conditions clear. |

An active EDM profile may command states such as `HDG`, `FLC`, a configured
airspeed reference, and a selected altitude. Those values should remain visible
in their normal state groups.

## Protection And ESP States

These states should not replace the active lateral or vertical mode. They add
messages or modify display priority.

| State | Display Label | Meaning |
|---|---|---|
| `PROTECTION_NONE` | none | No protection annunciation is active. |
| `PROTECTION_MINSPEED` | `MINSPEED` | Underspeed protection is active. |
| `PROTECTION_MAXSPEED` | `MAXSPEED` | Overspeed protection is active. |
| `ESP_ENABLED` | none or `ESP EQUIPPED` during startup | Electronic Stability and Protection is enabled. |
| `ESP_DISABLED` | `ESP OFF` | ESP is disabled. |
| `ESP_ACTIVE` | profile-dependent | ESP is currently applying a simulated protection response. |
| `ESP_FAIL` | `ESP FAIL` | ESP is unavailable because of a failure. |

ESP and protection behavior may not map cleanly to every MSFS aircraft and
should be treated as optional until the host adapter can provide reliable data.

## Smart Rudder Bias States

Smart Rudder Bias is optional and applies only to supported profiles.

| State | Display Label | Meaning |
|---|---|---|
| `RB_OFF` | `RB OFF` | Smart Rudder Bias is manually disabled. |
| `RB_ARMED` | none | Smart Rudder Bias is enabled and waiting for activation criteria. |
| `RB_ACTIVE_LEFT_ENGINE` | `RB`, `L ENG` | Smart Rudder Bias is active for a detected left-engine power loss. |
| `RB_ACTIVE_RIGHT_ENGINE` | `RB`, `R ENG` | Smart Rudder Bias is active for a detected right-engine power loss. |
| `RB_FAIL` | `RB FAIL` | Smart Rudder Bias is unavailable because of a failure. |

## Trim And Sensor Health States

These are health or alert states. They should not replace active flight director
modes.

| State | Display Label | Meaning |
|---|---|---|
| `TRIM_OK` | none | No trim failure or mistrim alert is active. |
| `PITCH_TRIM_FAIL` | `P TRIM FAIL` | Pitch trim has failed. |
| `YAW_TRIM_FAIL` | `Y TRIM FAIL` | Yaw trim has failed. |
| `ELEVATOR_MISTRIM_NOSE_UP` | `ELE TRIM` with direction | Nose-up elevator trim is required. |
| `ELEVATOR_MISTRIM_NOSE_DOWN` | `ELE TRIM` with direction | Nose-down elevator trim is required. |
| `AILERON_MISTRIM_LEFT` | `AIL TRIM` with direction | Left aileron trim is required. |
| `AILERON_MISTRIM_RIGHT` | `AIL TRIM` with direction | Right aileron trim is required. |
| `RUDDER_MISTRIM_LEFT` | `RUD TRIM` with direction | Left rudder trim is required. |
| `RUDDER_MISTRIM_RIGHT` | `RUD TRIM` with direction | Right rudder trim is required. |
| `AIRDATA_OK` | none | Required air data is available. |
| `AIRDATA_FAIL` | `AIRDATA FAIL` | Required air data is unavailable or invalid. |
| `ATTITUDE_OK` | none | Required attitude information is available. |
| `ATTITUDE_FAIL` | `NO ATTITUDE` | Required attitude information is unavailable; AFCS functions are inhibited. |

## Link And Simulator States

These are panel health states, not AFCS modes.

| State | Display Behavior |
|---|---|
| `LINK_OK` | Normal operation. |
| `LINK_STALE` | Show `LINK` or another configured warning while waiting for fresh host data. |
| `LINK_LOST` | Show `LINK`; keep local panel logic available for diagnostics. |
| `SIM_CONNECTED` | Normal operation. |
| `SIM_DISCONNECTED` | Show `SIM`. |

## Display Effect States

Display effects should be stored separately from the mode values.

| State | Meaning |
|---|---|
| `EFFECT_STEADY` | Render normally. |
| `EFFECT_SLOW_FLASH` | Slow attention flash. |
| `EFFECT_FAST_FLASH` | High-priority failure flash. |
| `EFFECT_INVERSE_FLASH` | Alternate normal and inverse video. |

The renderer should calculate the current visible phase. The state manager
should only select the effect and its start or expiry time.

## Messages, Events, And Data Are Not Mode States

The following items should not be placed in the lateral or vertical mode enums.

### Messages

- `PFT`
- `PFT FAIL`
- `AP FAIL`
- `EDM`
- `YD FAIL`
- `P TRIM FAIL`
- `Y TRIM FAIL`
- `ELE TRIM`
- `AIL TRIM`
- `RUD TRIM`
- `SET HDG=CRS`
- `DISABLED KEY`
- Key-stuck messages
- `AIRDATA FAIL`
- `NO ATTITUDE`
- `ESP EQUIPPED`
- `ESP OFF`
- `ESP FAIL`
- `RB OFF`
- `RB FAIL`
- `L ENG`
- `R ENG`
- `GLIDE`
- `TRACK MODE`
- `MINSPEED`
- `MAXSPEED`
- `LINK`
- `SIM`

### Input Or Host Events

- AP, FD, YD, HDG, NAV, APR, BC, ALT, VS, IAS, FLC, VNV, LVL, or GA button press
- Navigation course captured or lost
- Glidepath or glideslope captured or lost
- Selected altitude capture started or completed
- Navigation source changed
- Host link became stale or recovered
- Timer expired
- CWS pressed or released
- EDM armed, triggered, inhibited, activated, overridden, or cleared
- Protection, ESP, Smart Glide, Smart Rudder Bias, trim, or sensor health changed

### Reference Data

- Selected heading
- Selected altitude
- Selected vertical speed
- Selected IAS or FLC speed
- Pitch reference
- CDI or vertical deviation

## Recommended First Implementation Subset

Do not implement the complete catalog first. Start with the smallest useful
state model:

| Group | First States |
|---|---|
| System | `SYSTEM_BOOT`, `SYSTEM_READY` |
| Flight director | `FD_OFF`, `FD_ON` |
| Autopilot | `AP_OFF`, `AP_ON`, `AP_MANUAL_DISCONNECT` |
| Active lateral | `LAT_ACTIVE_NONE`, `LAT_ACTIVE_ROL`, `LAT_ACTIVE_HDG` |
| Armed lateral | `LAT_ARMED_NONE`, `LAT_ARMED_GPS` |
| Active vertical | `VERT_ACTIVE_NONE`, `VERT_ACTIVE_PIT`, `VERT_ACTIVE_ALT`, `VERT_ACTIVE_VS` |
| Armed vertical | `VERT_ARMED_NONE`, `VERT_ARMED_ALTS` |
| Navigation source | `NAV_SOURCE_NONE`, `NAV_SOURCE_GPS` |

This subset is enough to test:

1. FD or AP activation establishes `PIT` and `ROL`.
2. HDG selection replaces `ROL`.
3. NAV selection can arm `GPS`.
4. GPS capture can replace `HDG`.
5. VS can operate while `ALTS` remains armed.
6. AP disconnect can change AP status without destroying the FD mode state.

## Suggested File Ownership

| File | Responsibility |
|---|---|
| `modes.h` | Lateral, vertical, navigation source, and other mode-related enum types. |
| `state.h` | Complete runtime state structure containing the current values. |
| `events.h` | Events that request or report state changes. |
| `state_manager.h` | Public state manager functions. |
| `state_manager.c` | Initialization and all state transition logic. |
| `display_model.h` | Display labels, slots, effects, priorities, and expiry metadata. |
| `display_model.c` | Conversion from runtime state into a display snapshot. |

## Open Questions

- Should the first panel profile mimic the GMC 605C-IAS or GMC 605C-FLC
  variant?
- Should `TRACK MODE` be represented as an active lateral mode, a message, or
  both?
- Does the first target MSFS aircraft expose reliable VNAV, glidepath,
  glideslope, and protection states?
- Will the first firmware allow only one armed vertical mode, or will the
  display model need multiple simultaneous armed indications?
- Which optional feature groups belong in the first target aircraft profile:
  EDM, Smart Glide, ESP, Low Bank, or Smart Rudder Bias?
