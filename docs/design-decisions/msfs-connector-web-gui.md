# MSFS Connector Web GUI

## Goal

Define the preferred GUI for the Python MSFS connector.

The GUI should make the connector easy to run, inspect, and debug while keeping the ESP32 firmware simple.

No implementation code is included here.

## Sources Used

- User restart instruction: create a GUI for the Python MSFS connector, preferably web GUI.
- Existing project connector and protocol notes.
- Microsoft Flight Simulator SDK SimConnect API reference: https://docs.flightsimulator.com/html/Programming_Tools/SimConnect/SimConnect_API_Reference.htm

## Decision

Use a local web GUI served by the Python connector.

Recommended first shape:

- Python connector process owns SimConnect, ESP32 serial link, state snapshots, and command mapping.
- Browser UI connects to the local connector.
- GUI is for monitoring, testing, and configuration.
- ESP32 still talks only to the connector protocol.

## Why Web GUI

- Easy to open from VSCode workflow.
- Works well for logs, tables, and live state.
- Avoids native desktop GUI complexity.
- Can expose debug buttons without touching ESP32 firmware.
- Can later run on another device on the LAN if needed.

## Main Screens

| Screen | Purpose |
|---|---|
| Dashboard | MSFS connection, ESP32 connection, aircraft profile, current snapshot age. |
| Live State | AP/FD/YD, lateral/vertical labels, selected references, raw key SimVars. |
| Command Console | Buttons for AP, FD, HDG, NAV, APR, ALT, VS, FLC/IAS, disconnect. |
| ESP32 Link | Serial port, baud rate, packet counters, malformed packets, last heartbeat. |
| Aircraft Profile | Selected aircraft adapter, supported events, unsupported commands. |
| Logs | Timestamped SimConnect events, ESP32 commands, rejected commands, errors. |

## Dashboard Minimum

The first useful GUI should show:

- MSFS connected/disconnected.
- Aircraft title/profile.
- ESP32 connected/disconnected.
- Serial port and baud rate.
- Last snapshot timestamp.
- Last ESP32 heartbeat.
- Current AP/FD/YD values.
- Current lateral/vertical labels.
- Last command and result.

## Debug Controls

Include connector-side buttons before relying on physical hardware:

| Control | Use |
|---|---|
| Send fake snapshot | Test ESP32 display without MSFS. |
| Toggle AP command | Test SimConnect event mapping. |
| HDG/NAV/APR/ALT/VS/FLC buttons | Test AP command path. |
| Encoder step controls | Test reference changes. |
| Force link stale/lost | Test ESP32 error display. |
| Export log | Save a short debugging session. |

## Connector Responsibilities

The GUI should not bypass the connector architecture.

The connector still owns:

- SimConnect connection.
- SimVar polling.
- SimConnect event transmission.
- Aircraft adapter selection.
- ESP32 packet encoding/decoding.
- Snapshot creation.
- Command result reporting.

The GUI only observes and sends debug/user commands into that connector core.

## Recommended Web Stack

Keep it boring:

| Layer | Recommendation |
|---|---|
| Backend | Python HTTP server from the connector process. |
| Live updates | WebSocket or Server-Sent Events. |
| Frontend | Simple HTML/CSS/JS first. |
| Packaging | Run from VSCode terminal first; package later if needed. |

Avoid a large frontend framework until the connector behavior is stable.

## Safety And Scope Boundary

- This GUI is for MSFS only.
- It is not a certified avionics test tool.
- It must clearly show when data is stale or disconnected.
- It should never hide command failures.
- It should avoid optimistic AP mode display; show confirmed connector state.

## Recommended Next Step

Create a connector GUI skeleton with three live panels first:

1. Connection status.
2. Current display snapshot.
3. Command/log stream.
