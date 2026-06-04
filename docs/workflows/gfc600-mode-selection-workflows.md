# GFC 600-Style Mode Selection Workflows

This workflow converts Garmin GFC 600 behavior into practical steps for the MSFS/ESP32 panel.

Primary source: Garmin `GFC 600 Automatic Flight Control System (with Color Display) Pilot's Guide`, `190-03090-00 Rev. A`, January 2024.

Detailed FD/AP-off behavior and confidence notes:

- [GFC 600 Mode-Key Behavior With FD And AP Off](../research/gfc600-mode-key-behavior-fd-ap-off.md)

## Workflow 0: Mode Key With FD And AP Off

```mermaid
flowchart TD
    Press[Mode key pressed] --> Valid{Mode selection valid?}
    Valid -->|no| Reject[Keep FD, AP, and modes unchanged]
    Valid -->|yes| EnableFD[Enable FD]
    EnableFD --> Axis{Selected mode axis}
    Axis -->|lateral| Lat[Set selected lateral mode]
    Axis -->|vertical| Vert[Set selected vertical mode]
    Axis -->|coupled| Coupled[Set both axes]
    Lat --> PIT[Set vertical PIT if none]
    Vert --> ROL[Set lateral ROL if none]
    Coupled --> Special{Special coupled mode}
    Special -->|LVL| EngageAP[Engage AP]
    Special -->|GA| KeepAPOff[Keep AP off]
```

Project behavior:

- `AP_ON` with `FD_OFF` is not a valid normal state.
- A successful ordinary mode selection while FD is off enables FD, but does not
  engage AP.
- Lateral selections use `PIT` as the default vertical mode.
- Vertical selections use `ROL` as the default lateral mode.
- `LVL` engages AP and selects `LVL` on both axes.
- `GA` selects `GA` on both axes but does not engage AP from an off state.
- Invalid `NAV`, `APR`, `BC`, or `VNV` requests do not change FD, AP, or mode
  state.

## Workflow 1: AP/FD Engagement

```mermaid
flowchart TD
    Start[Button press] --> Btn{Pressed button}
    Btn -->|FD| FDOn[FD on]
    Btn -->|AP and FD off| APDefault[FD on, AP on]
    Btn -->|AP and FD on| APFollow[AP on, follow active FD modes]

    FDOn --> Modes[PIT + ROL default]
    APDefault --> Modes
    APFollow --> Keep[Keep current active/armed modes]
    Modes --> ALTS{Selected altitude capture available?}
    ALTS -->|yes| ArmALTS[Arm ALTS]
    ALTS -->|no| Done[Done]
    ArmALTS --> Done
    Keep --> Done
```

Project behavior:

1. On FD from off: active vertical `PIT`, active lateral `ROL`.
2. On AP from FD off: FD on, AP on, active `PIT`/`ROL`.
3. On AP from FD on: AP on, preserve existing modes.
4. If selected-altitude capture exists, arm `ALTS` for compatible vertical modes.
5. Prevent or correct the invalid runtime combination `AP_ON` with `FD_OFF`.

## Workflow 2: Vertical Mode Button

```mermaid
flowchart TD
    Press[Vertical button pressed] --> Mode{Mode}
    Mode -->|ALT| ALT[Set ALT active, altitude ref = current or captured altitude]
    Mode -->|VS| VS[Set VS active, VS ref = current VS]
    Mode -->|IAS| IAS[Set IAS active, airspeed ref = current IAS]
    Mode -->|FLC| FLC[Set FLC active, airspeed/Mach ref = current value]
    Mode -->|VNV| VNV[Arm VPTH if valid VNAV path]
    Mode -->|APR with GPS| GP[Arm GP]
    Mode -->|APR with LOC/ILS| GS[Arm GS]

    VS --> ALTS{Selected altitude capture available?}
    IAS --> ALTS
    FLC --> ALTS
    ALTS -->|yes| Arm[Arm ALTS]
    ALTS -->|no| Done[Done]
    ALT --> Done
    VNV --> Done
    GP --> Done
    GS --> Done
    Arm --> Done
```

Project behavior:

- `VS`: reference changes in 100 fpm steps.
- `IAS`: reference changes in 1 kt steps.
- `FLC`: reference changes in 1 kt or Mach 0.01 steps depending aircraft.
- `ALT`: reference changes in 10 ft steps. Garmin allows limited adjustment around current altitude; for MSFS mimic, start with +/-200 ft.
- `PIT`: reference changes in 0.5 deg steps.

## Workflow 3: Selected Altitude Capture

```mermaid
flowchart TD
    Active[Active PIT/VS/IAS/FLC/GA] --> Armed[ALTS armed]
    Armed --> Near{Nearing selected altitude?}
    Near -->|no| Armed
    Near -->|yes| Capture[ALTS active, ALT armed]
    Capture --> Fifty{Within about 50 ft?}
    Fifty -->|no| Capture
    Fifty -->|yes| Hold[ALT active, hold selected altitude]
```

Project behavior:

- Use MSFS current altitude, selected altitude, and vertical speed sign to determine closure.
- When `ALTS` becomes active, flash/attention behavior may be applied.
- At approximately 50 ft from target, transition to `ALT`.

## Workflow 4: Lateral NAV/APR Selection

```mermaid
flowchart TD
    Press[NAV or APR pressed] --> Source{Selected nav source}
    Source -->|GPS| GPS[Candidate label GPS]
    Source -->|VOR| VOR[Candidate label VOR or VAPP for APR]
    Source -->|LOC| LOC[Candidate label LOC]

    GPS --> Deviation{CDI greater than half scale?}
    VOR --> Deviation
    LOC --> Deviation

    Deviation -->|yes| Armed[Keep current lateral active, set armed lateral]
    Deviation -->|no| Active[Set selected lateral active]
    Armed --> Capture{Course captured?}
    Capture -->|yes| Active
```

Project behavior:

- `NAV` follows GPS roll steering if available; otherwise course/deviation.
- `APR` is similar but approach-sensitive and can arm vertical `GP` or `GS`.
- VOR approach should show `VAPP` on a GMC-style display. If using GI 285 style, show `VOR`.
- If source changes while NAV/APR is active and autoswitching is not configured, revert lateral active mode to `ROL`.

## Workflow 5: Coupled LVL Mode

```mermaid
flowchart TD
    LVL[LVL pressed] --> AP{AP engaged?}
    AP -->|no| EngageAP[Engage AP]
    AP -->|yes| Cancel[Cancel active and armed modes]
    EngageAP --> Cancel
    Cancel --> Set[Set lateral LVL and vertical LVL]
    Set --> Refs[Command 0 fpm vertical reference and 0 bank lateral reference]
    Refs --> Exit{Other mode selected?}
    Exit -->|yes| NewMode[Leave LVL for selected mode]
```

Project behavior:

- `LVL` owns both lateral and vertical labels.
- It should clear armed modes.
- It does not track altitude or heading.

## Workflow 6: Coupled GA Mode

```mermaid
flowchart TD
    GA[GA button pressed] --> SetGA[Set lateral GA and vertical GA]
    SetGA --> Arm{Selected altitude capture available?}
    Arm -->|yes| ArmALTS[Arm ALTS]
    Arm -->|no| Active[Remain GA]
    ArmALTS --> Active
    Active --> Modify{CWS or pitch wheel attitude modification?}
    Modify -->|yes| Revert[Revert to PIT + ROL]
    Modify -->|no| Active
```

Project behavior:

- `GA` owns both lateral and vertical labels.
- Use a configured nose-up pitch reference for the simulated aircraft.
- If the project cannot safely command pitch in MSFS for a chosen aircraft, still display `GA` and send the closest available MSFS TOGA/go-around event.

## Workflow 7: VNAV to Approach

```mermaid
flowchart TD
    Setup[GPS flight plan with constraints] --> VNV[VNV pressed]
    VNV --> VPTHArmed[VPTH armed]
    VPTHArmed --> TOD{At TOD/path intercept?}
    TOD -->|yes| VPTH[VPTH active]
    VPTH --> Constraint{Constraint altitude capture?}
    Constraint -->|yes| ALTV[ALTV active]
    ALTV --> VPTH
    VPTH --> Approach{Approach armed?}
    Approach -->|GPS APR| GPArmed[GP armed]
    Approach -->|ILS APR| GSArmed[LOC and GS armed]
    GPArmed --> GP[GP active at glidepath capture]
    GSArmed --> LOCGS[LOC/GS active at capture]
```

Project behavior:

- Treat VNAV as advanced/phase-2 unless the selected MSFS aircraft exposes usable VNAV state.
- For first implementation, support labels and arming, then validate capture behavior in sim.

