# Panel Integration Test Plan

## Goal

Validate the restarted system:

- Python connector reads MSFS.
- ESP32 displays connector snapshots.
- ESP32 sends button/encoder commands.
- Python connector sends commands to MSFS.
- MSFS state comes back and updates the display.

This is a simulator-only test plan.

## Sources Used

- User restart instruction.
- Garmin `GFC 600 Pilot's Guide`, `190-01488-00 Rev. H`.
- [Firmware Architecture](../design-decisions/gmc605-firmware-architecture.md)
- [MSFS SimVar And Event Map](../research/msfs-gmc605-simvar-event-map.md)
- [Display Annunciation Model](../state-machines/gfc600-mode-logic.md)

## Test Setup Record

Record this for each test run:

| Field | Value |
|---|---|
| Date/time | |
| MSFS version | |
| Aircraft | |
| Connector profile | |
| ESP32 board | |
| Display module | |
| Link type | USB CDC / UART / Wi-Fi |
| Snapshot rate | |
| Notes | |

## Phase 1: Connector Without ESP32

| Test | Action | Pass Criteria |
|---|---|---|
| Connect to MSFS | Start connector with MSFS running. | GUI shows MSFS connected and aircraft detected. |
| Read AP state | Toggle AP in virtual cockpit. | Connector AP state changes without ESP32. |
| Read selected heading | Move heading bug in MSFS. | Connector shows the new heading. |
| Read selected altitude | Change selected altitude in MSFS. | Connector shows the new altitude. |
| Send AP event | Press AP command in connector/debug control. | MSFS AP changes or connector reports command failure. |
| Send HDG event | Press HDG command in connector/debug control. | MSFS changes HDG state or reports unsupported behavior. |
| No optimistic mode | Press any connector command. | Display snapshot changes only after read-back state changes. |

## Phase 2: Web GUI And Debug Snapshot

Use connector debug snapshots. No COM port or ESP32 is required.

| Test | Action | Pass Criteria |
|---|---|---|
| Start web debug | Run connector in web debug mode. | GUI opens and polls snapshots. |
| SVG panel | Load the web page. | GMC 605 SVG panel is visible with LCD and LED overlays aligned. |
| LCD slots | Set lateral/vertical active and armed modes. | Left LCD shows lateral active/armed; center LCD shows vertical active/armed and reference. |
| AP/FD/YD LEDs | Toggle AP, FD, and YD in the snapshot editor. | Key-adjacent LEDs change; AP/FD/YD do not appear as normal LCD text. |
| GMC lateral labels | Set `GPS`, `VOR`, `LOC`, `VAPP`, and `BC`. | LCD displays the same real GMC 605 label, with `VAPP` used for VOR approach. |
| Empty armed mode | Set armed modes to `NONE`. | Armed LCD fields are blank. |
| Reference editing | Change heading, altitude, VS, and speed. | Reference area and data sections update without hand-editing JSON. |
| Aircraft data editing | Change aircraft heading, altitude, VS, airspeed, CDI, and GSI. | Snapshot endpoint returns the changed values. |
| Messages | Add up to four messages. | Message area shows short status/alert text. |

## Phase 3: ESP32 Without MSFS

Use connector debug snapshots.

| Test | Action | Pass Criteria |
|---|---|---|
| Boot display | Power ESP32. | OLED shows boot/PFT or link status. |
| Link waiting | Do not start connector. | OLED shows `LINK`. |
| Fake snapshot | Send debug snapshot from connector. | OLED shows expected labels and LED states. |
| Snapshot update | Change fake AP/HDG/ALT labels. | OLED updates without reboot. |
| Blink/inverse | Send alert style. | OLED blink/inverse timing is readable. |
| Button command | Press each panel button. | Connector receives the correct semantic command. |
| Encoder command | Rotate each encoder. | Connector receives correct increment/decrement events. |
| Link stale | Stop connector packets. | OLED marks stale/lost link within timeout. |

## Phase 4: Full MSFS Loop

| Test | Action | Pass Criteria |
|---|---|---|
| MSFS to OLED | Toggle AP in virtual cockpit. | OLED follows MSFS state. |
| OLED not optimistic | Press ESP32 AP button. | OLED changes only after connector sends updated snapshot. |
| AP button | Press ESP32 AP. | MSFS AP changes, then OLED updates. |
| FD button | Press ESP32 FD. | MSFS FD changes, then OLED updates. |
| HDG button | Press ESP32 HDG. | MSFS HDG state changes or connector reports unsupported command. |
| NAV/APR buttons | Press ESP32 NAV/APR in valid scenarios. | Connector logs event and OLED shows MSFS-derived result. |
| ALT button | Press ESP32 ALT. | MSFS ALT state changes, then OLED updates. |
| VS/FLC/IAS | Press selected speed/vertical mode buttons. | OLED follows target aircraft behavior. |
| Reference encoders | Turn HDG/ALT/VS/speed controls. | MSFS selected reference changes and OLED follows. |
| AP disconnect | Trigger AP disconnect. | AP LED/status follows snapshot alert timing; LCD message area shows relevant alert if supplied. |

## Phase 5: Failure And Edge Tests

| Test | Action | Pass Criteria |
|---|---|---|
| MSFS closes | Close MSFS while connector stays running. | GUI and OLED show `SIM` or disconnected state. |
| Connector closes | Stop connector while ESP32 runs. | OLED shows `LINK` after timeout. |
| Bad packet | Inject malformed snapshot. | ESP32 ignores it and keeps previous valid display. |
| Unsupported command | Send command not mapped for aircraft. | GUI reports rejected/unsupported; OLED does not invent state. |
| Rapid button presses | Press buttons quickly. | Debounce prevents duplicate accidental commands. |
| Encoder burst | Spin encoder quickly. | Connector receives bounded, ordered increments. |
| Unknown mode | Force an unmapped SimVar combination. | Connector leaves the slot blank or uses a debug marker; ESP32 does not guess. |

## Pass Criteria

The project passes the restart validation when:

- The ESP32 never claims a mode changed before MSFS/connector state confirms it.
- The connector GUI shows MSFS connection, ESP32 connection, last snapshot, and command log.
- The OLED/LCD model shows lateral and vertical mode labels, selected references,
  AP/FD/YD LED states, and link/sim faults in the correct regions.
- AP/FD/YD are rendered as key-adjacent indicators, not normal LCD text.
- Every physical input creates the expected connector command.
- Link loss and MSFS disconnect are obvious on the display.

## Recommended Next Step

Run Phase 1 and Phase 2 before doing any aircraft-specific AP mode tuning.
