# GFC 600-Style Mode State Machines

This document converts Garmin GFC 600 pilot-guide behavior into simulator-oriented state machines for the ESP32/MSFS project.

Primary source: Garmin `GFC 600 Automatic Flight Control System (with Color Display) Pilot's Guide`, `190-03090-00 Rev. A`, January 2024.

Simulator boundary: this describes display and MSFS control logic only. It is not real aircraft autopilot guidance logic.

## State Model

Use independent but coordinated state groups:

| Group | Example State |
|---|---|
| Flight director | `fd_off`, `fd_on` |
| Autopilot | `ap_off`, `ap_on`, `ap_manual_disconnect_flash`, `ap_fail` |
| Yaw damper | `yd_off`, `yd_on`, `yd_disconnect_flash`, `yd_fail` |
| Active lateral | `ROL`, `HDG`, `GPS`, `VOR`, `LOC`, `BC`, `LVL`, `GA` |
| Armed lateral | none, `GPS`, `VOR`, `LOC`, `BC` |
| Active vertical | `PIT`, `ALT`, `VS`, `IAS`, `FLC`, `VPTH`, `GP`, `GS`, `LVL`, `GA`, `ALTS`, `ALTV` |
| Armed vertical | none, `ALTS`, `ALT`, `VPTH`, `GP`, `GS` |
| Reference values | pitch ref, altitude ref, VS ref, IAS/FLC ref |
| Messages | `PFT`, `PFT FAIL`, `MINSPEED`, `MAXSPEED`, `ESP OFF`, `SET HDG=CRS`, etc. |

## Startup and Default Modes

```mermaid
stateDiagram-v2
    [*] --> PowerOff
    PowerOff --> PFT: power applied
    PFT --> Ready: preflight test passed
    PFT --> Fail: preflight test failed

    Ready --> FD_On_Default: FD pressed
    Ready --> AP_On_Default: AP pressed and FD off
    FD_On_Default --> AP_On_FollowFD: AP pressed

    state FD_On_Default {
        [*] --> PIT_ROL
        PIT_ROL: active vertical PIT
        PIT_ROL: active lateral ROL
        PIT_ROL: ALTS armed if selected-alt capture available
    }

    state AP_On_Default {
        [*] --> AP_PIT_ROL
        AP_PIT_ROL: AP engaged
        AP_PIT_ROL: FD active PIT/ROL
    }
```

Implementation notes:

- If AP is pressed while FD is off, set FD on and initialize `PIT`/`ROL`.
- If FD is already on, AP engagement should not change the active modes.
- If YD exists and should auto-engage with AP in the chosen simulated installation, model that as configuration.

## Vertical Mode State Machine

```mermaid
stateDiagram-v2
    [*] --> PIT: FD/AP default

    PIT --> VS: VS pressed
    PIT --> IAS: IAS pressed
    PIT --> FLC: FLC pressed
    PIT --> ALT: ALT pressed
    PIT --> GA: GA button
    PIT --> LVL: LVL pressed

    VS --> ALTS: nearing selected altitude
    IAS --> ALTS: nearing selected altitude
    FLC --> ALTS: nearing selected altitude
    GA --> ALTS: nearing selected altitude
    PIT --> ALTS: nearing selected altitude

    ALTS --> ALT: within about 50 ft of selected altitude
    ALT --> VS: VS pressed
    ALT --> IAS: IAS pressed
    ALT --> FLC: FLC pressed
    ALT --> PIT: pitch wheel/CWS if mode-specific reversion needed

    PIT --> VPTH_Armed: VNV pressed and valid VNAV profile
    ALT --> VPTH_Armed: VNV pressed and valid VNAV profile
    VS --> VPTH_Armed: VNV pressed and valid VNAV profile
    IAS --> VPTH_Armed: VNV pressed and valid VNAV profile
    FLC --> VPTH_Armed: VNV pressed and valid VNAV profile
    VPTH_Armed --> VPTH: TOD/path captured
    VPTH --> ALTV: constraint altitude capture
    ALTV --> VPTH: after constraint level-off, next VNAV leg

    PIT --> GP_Armed: APR pressed, GPS approach valid
    PIT --> GS_Armed: APR pressed, LOC/ILS approach valid
    GP_Armed --> GP: glidepath captured
    GS_Armed --> GS: glideslope captured

    LVL --> PIT: another vertical mode pressed
    GA --> PIT: CWS or nose wheel attitude modification
```

### Vertical Label Rules

| Event/Condition | Active Vertical | Armed Vertical | Reference |
|---|---|---|---|
| FD/AP starts | `PIT` | `ALTS` if available | pitch ref |
| `ALT` pressed | `ALT` | none | altitude ref |
| `VS` pressed | `VS` | `ALTS` if available | VS ref |
| `IAS` pressed | `IAS` | `ALTS` if available | IAS ref |
| `FLC` pressed | `FLC` | `ALTS` if available | IAS/Mach ref |
| Approaching selected altitude | `ALTS` | `ALT` | selected altitude |
| Within about 50 ft of selected altitude | `ALT` | none | selected altitude |
| `VNV` armed and path captured | `VPTH` | possible `ALTV`, `GP`, or `GS` depending phase | path/constraint |
| GPS APR armed | current vertical mode | `GP` | existing ref |
| GPS glidepath captured | `GP` | normally none | glidepath |
| LOC APR armed with glideslope | current vertical mode | `GS` | existing ref |
| ILS glideslope captured | `GS` | normally none | glideslope |
| `LVL` pressed | `LVL` | none | 0 fpm target |
| `GA` pressed | `GA` | `ALTS` if available | fixed GA pitch target |

## Lateral Mode State Machine

```mermaid
stateDiagram-v2
    [*] --> ROL: FD/AP default

    ROL --> HDG: HDG pressed
    ROL --> GPS_Armed: NAV pressed, GPS selected, CDI > half scale
    ROL --> GPS: NAV pressed, GPS selected, CDI <= half scale
    ROL --> VOR_Armed: NAV pressed, VOR selected, CDI > half scale
    ROL --> VOR: NAV pressed, VOR selected, CDI <= half scale
    ROL --> LOC_Armed: NAV pressed, LOC selected, CDI > half scale
    ROL --> LOC: NAV pressed, LOC selected, CDI <= half scale

    GPS_Armed --> GPS: course captured
    VOR_Armed --> VOR: course captured
    LOC_Armed --> LOC: course captured

    HDG --> GPS_Armed: NAV pressed, GPS selected, CDI > half scale
    HDG --> GPS: NAV pressed, GPS selected, CDI <= half scale
    HDG --> VOR_Armed: NAV pressed, VOR selected, CDI > half scale
    HDG --> VOR: NAV pressed, VOR selected, CDI <= half scale
    HDG --> LOC_Armed: NAV pressed, LOC selected, CDI > half scale
    HDG --> LOC: NAV pressed, LOC selected, CDI <= half scale

    GPS --> ROL: unsupported nav source change
    VOR --> ROL: nav signal invalid or source/frequency change
    LOC --> ROL: unsupported nav source change

    GPS --> GPS_APR_Armed: APR pressed for GPS approach
    GPS_APR_Armed --> GPS: approach course captured
    VOR --> VAPP_Armed: APR pressed for VOR approach
    VAPP_Armed --> VAPP: approach course captured
    LOC --> LOC_APR_Armed: APR pressed for LOC approach
    LOC_APR_Armed --> LOC: localizer captured

    ROL --> BC_Armed: BC pressed and not captured
    ROL --> BC: BC pressed and captured
    BC_Armed --> BC: backcourse captured

    HDG --> LVL: LVL pressed
    GPS --> LVL: LVL pressed
    VOR --> LVL: LVL pressed
    LOC --> LVL: LVL pressed
    BC --> LVL: LVL pressed
    LVL --> ROL: another lateral mode selected

    ROL --> GA: GA button
    HDG --> GA: GA button
    GPS --> GA: GA button
    VOR --> GA: GA button
    LOC --> GA: GA button
    GA --> ROL: CWS or attitude modification
```

### Lateral Label Rules

| Event/Condition | Active Lateral | Armed Lateral |
|---|---|---|
| FD/AP starts | `ROL` | none |
| Bank at ROL activation less than 6 deg | `ROL` | wings-level command |
| Bank 6 to 25 deg | `ROL` | bank hold command |
| Bank more than 25 deg | `ROL` | limit command to 25 deg |
| `HDG` pressed | `HDG` | none |
| `NAV` pressed, CDI more than half scale | previous active mode | selected source armed: `GPS`, `VOR`, or `LOC` |
| `NAV` pressed, CDI less than half scale | `GPS`, `VOR`, or `LOC` | none |
| `APR` pressed, CDI more than half scale | previous active mode | selected approach armed |
| `APR` pressed, CDI less than half scale | approach mode active | none |
| GPS approach active | `GPS` | vertical `GP` may be armed |
| VOR approach active | `VAPP` on GMC, `VOR` on GI 285 | none |
| LOC approach active | `LOC` | vertical `GS` may be armed |
| `BC` pressed and captured | `BC` | none |
| `LVL` pressed | `LVL` | none |
| `GA` pressed | `GA` | none |
| Unsupported source switch while NAV/APR active | `ROL` | none |

## Display Annunciation State Machine

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Armed: mode selected but not captured
    Armed --> CaptureFlash: capture occurs
    CaptureFlash --> Normal: flash timer expires

    Normal --> ManualDisconnect: AP/YD manually disconnected
    ManualDisconnect --> Normal: about 5 sec flash timer expires

    Normal --> Failure: AP/YD/trim failure
    Failure --> Normal: fault cleared or power cycle in simulator

    Normal --> Message: advisory/status message active
    Message --> Normal: message cleared
```

Recommended implementation:

- Store display attributes separately from mode values:
  - `label`
  - `slot`
  - `color`
  - `flash`
  - `inverse_video`
  - `priority`
  - `expires_at_ms`
- This keeps mode logic clean and makes OLED rendering predictable.

## MSFS Mapping Notes

Do not make the first version too clever. Start with these local concepts:

- Button event changes local Garmin-style state.
- Local state sends best-match MSFS AP event.
- MSFS simvars confirm whether airplane is following expected behavior.
- Display follows local Garmin-style state, corrected only by strong MSFS evidence such as AP disconnect, selected nav source, or selected altitude.

