# Project Status

## Current Direction

The project has been restarted as an MSFS display/input panel.

- MSFS owns autopilot logic.
- The Python connector owns SimConnect, aircraft adapters, command mapping, and snapshot creation.
- The ESP32 will own buttons, encoders, OLED rendering, link health, and local diagnostics.
- ESP32 button presses are command requests only.
- The OLED updates from connector snapshots, not from local autopilot logic.

## Firmware Reset

The previous firmware implementation was removed.

Current firmware is a minimal empty ESP-IDF project:

- `firmware/CMakeLists.txt`
- `firmware/main/CMakeLists.txt`
- `firmware/main/main.c`
- `firmware/sdkconfig.defaults`

There are no firmware components, no protocol code, and no local autopilot logic in the firmware tree now.

## Documentation Refresh

The docs were simplified around the new ownership model:

- Firmware architecture now describes display/input firmware only.
- Mode logic was reduced to a display annunciation model and rechecked against
  the GMC 605 LCD/LED layout in the Garmin pilot guide.
- SimVar/event mapping is focused on the Python connector.
- Test planning now validates the full MSFS -> connector -> ESP32 -> connector -> MSFS loop.
- A web GUI design document was added for the Python connector.
- The docs now use real GMC 605 lateral labels in snapshots: `GPS`, `VOR`,
  `LOC`, `VAPP`, `BC`, `HDG`, `ROL`, `LVL`, and `GA`.
- AP/FD/YD remain key LED states, not normal LCD text.

## Python Connector

The Python connector remains as the active PC-side application.

- Headless debug/MSFS connector modes are present.
- A local web GUI is present under `msfs_connector/src/gmc605_connector/web.py`.
- The web GUI can run in debug mode without ESP32 hardware.
- The web GUI can optionally forward snapshots and receive commands through a serial transport.
- The web GUI now renders a purpose-built, high-resolution GMC 605 vector
  faceplate `msfs_connector/src/img/gmc605_panel.svg`. Its bezel, keys, LED
  dots and LCD glass are placed using geometry extracted 1:1 from the original
  fabrication drawing `gfc600_tinkercad.svg` (still served at
  `/assets/gfc600_tinkercad.svg` for reference).
- Live LCD annunciations are overlaid on the faceplate using the real GMC 605
  display layout as a four-column / two-row grid: lateral active/armed (left),
  vertical active/armed (center), mode reference (center-right), and the message
  area (right).
- Display rules now follow the real unit: active modes are large green, armed
  modes are smaller white, references are cyan, a captured mode flashes
  (inverse video) for ~10 s, and manual AP/YD disconnect flashes the matching
  key LED amber for ~5 s. Attention messages (FAIL / NO SIM / LINK / DISABLD)
  render in amber.
- AP, FD, and YD are LED overlays beside their keys, not LCD text.
- The control variables sent to the ESP32 are split into two clear sections:
  a "GMC 605 Controller" (engagement, mode annunciations, pilot-selected
  references) and a separate "Sim / Aircraft State" (SIM connected, nav source
  GPS/LOC/VOR, aircraft heading/altitude/VS/airspeed, and CDI/GSI needles).
- Both sections share presets, quick nav/source buttons, step buttons, and an
  "Apply To ESP32" action; focused fields are not overwritten by live polling.

## Next Work

1. Confirm ESP-IDF environment path and build the empty firmware project.
2. Choose the ESP32 board/variant and UART or USB CDC host-link path.
3. Bring up a static OLED display test.
4. Add button/encoder scanning and send command packets to the connector.
5. Pick the first target MSFS aircraft profile.

## Validation

- Python connector tests pass: `python -m unittest discover -s tests -v`
  from `msfs_connector` ran 16 tests successfully.
- Firmware build was not rerun because `idf.py` was not available in the current PowerShell PATH.
- Current mode/display logic was verified against Garmin `GFC 600 Pilot's Guide`
  `190-01488-00 Rev. H` and the project docs were updated accordingly.
