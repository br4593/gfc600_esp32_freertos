# Project Documentation

This is an MSFS-only Garmin GMC 605 / GFC 600-style simulator panel.

The new project rule is simple:

- MSFS owns autopilot behavior.
- The Python connector talks to MSFS through SimConnect.
- The ESP32 shows the latest connector snapshot on the OLED.
- The ESP32 sends button and encoder commands back to the connector.
- The ESP32 does not implement autopilot mode logic.

## Current Core Documents

| Document | Purpose |
|---|---|
| [Firmware Architecture](design-decisions/gmc605-firmware-architecture.md) | ESP32 display/input firmware shape and task ownership. |
| [MSFS Connector Web GUI](design-decisions/msfs-connector-web-gui.md) | Planned browser GUI for the Python connector. |
| [MSFS SimVar And Event Map](research/msfs-gmc605-simvar-event-map.md) | Minimal SimConnect reads, events, and adapter rules. |
| [Display Annunciation Model](state-machines/gfc600-mode-logic.md) | Display labels and snapshot fields, not firmware-owned AP logic. |
| [Display And ESP32 Selection](design-decisions/gmc605-display-and-esp32-selection.md) | Hardware/display decision for the simulator panel. |
| [Panel Integration Test Plan](test-plans/gfc600-mode-logic-test-plan.md) | Tests for connector, ESP32 display, and command flow. |
| [MSFS Connector README](../msfs_connector/README.md) | Existing Python connector notes and runnable details. |

## Editing Rules

- Keep firmware docs about ESP32 inputs, display, link health, and rendering.
- Keep SimConnect details in the SimVar/event map.
- Keep connector UI decisions in the web GUI document.
- Keep display label decisions in the annunciation model.
- Do not add Garmin-style transition engines to ESP32 documentation.
- Do not describe this as real aircraft avionics.

## First Restart Target

Build a working loop before adding polish:

1. Python connector reads MSFS state.
2. Python connector sends a compact snapshot to ESP32.
3. ESP32 displays AP/FD/YD key LEDs, lateral/vertical LCD labels, references,
   and link status.
4. ESP32 sends button/encoder commands to Python.
5. Python sends SimConnect events to MSFS.
6. Python reads back the result and sends the next snapshot.
