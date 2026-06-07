# GFC 600 MSFS Panel Documentation

This project is an MSFS-only physical GMC 605-style panel. It is not intended
for real aircraft or certified use.

## Read In This Order

| Document | One clear purpose |
|---|---|
| [GFC600_LOGIC.md](GFC600_LOGIC.md) | Defines the real GFC 600 modes, transitions, and annunciations we want to mimic. |
| [MSFS_MAPPING.md](MSFS_MAPPING.md) | Maps generic MSFS SimVars into canonical GFC 600 modes and marks uncertain mappings. |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | Defines system ownership, implementation phases, and validation scenarios. |
| [ESP32 Connector Output Protocol](workflows/esp32-connector-output-protocol.md) | Defines the current UART/JSON output for ESP32 parser and renderer implementation. |

`GFC600_LOGIC.md` is the behavioral source of truth. `MSFS_MAPPING.md` explains
how much of that behavior MSFS can prove. `PROJECT_PLAN.md` defines how to build
and test the connector without mixing those two concerns.

## System Rule

```text
MSFS aircraft state
  -> Python connector maps it into canonical GFC 600-style state
  -> Web GUI and future ESP32 render the connector snapshot
```

MSFS owns actual flight-control behavior. The connector owns interpretation and
aircraft-specific mapping. The ESP32 will eventually own physical inputs and
rendering only.

## Modeling Principle

The canonical AFCS state is not one mode enum. It contains parallel engagement,
lateral, vertical, protection, and attention regions. This allows valid states
such as `HDG` active with `GPS` armed while `VS` is active with both `ALTS` and
`GP` armed.

## Primary Sources

- Garmin GFC 600 Pilot's Guide, `190-01488-00 Rev. H`:
  https://static.garmin.com/pumac/190-01488-00_h.pdf
- MSFS Aircraft Autopilot/Assistant Variables:
  https://docs.flightsimulator.com/html/Programming_Tools/SimVars/Aircraft_SimVars/Aircraft_AutopilotAssistant_Variables.htm
- MSFS Aircraft Autopilot/Flight Assist Events:
  https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Autopilot_Flight_Assist_Events.htm
