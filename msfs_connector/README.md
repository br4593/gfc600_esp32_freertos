# GMC 605 MSFS Connector

Windows-side connector for the ESP32 GMC 605-style MSFS panel.

MSFS remains the authority for autopilot logic. The connector is the bridge
between the simulator and the panel:

- ESP32 button and encoder packets are command requests.
- MSFS mode and reference data is read back after commands and periodic polls.
- The connector sends confirmed or derived display snapshots to the ESP32.
- Debug mode provides the same UART protocol without requiring MSFS.

## Install

Create a virtual environment from `msfs_connector/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[msfs]"
```

Debug mode only needs the base install:

```powershell
python -m pip install -e .
```

## Find The ESP32 Port

```powershell
python -m gmc605_connector --list-ports
```

## Simple Interactive Launch

Launch without arguments:

```powershell
python -m gmc605_connector
```

The connector asks whether to use Debug or MSFS mode, then asks which detected
serial port belongs to the ESP32. Debug is the default mode when Enter is
pressed.

## Run With MSFS

Start MSFS and load an aircraft before starting the connector:

```powershell
python -m gmc605_connector --mode msfs --port COM5
```

SimConnect startup is bounded to 5 seconds by default, so a stalled simulator
does not leave the headless connector hanging. Adjust it when needed:

```powershell
python -m gmc605_connector --mode msfs --port COM5 --source-open-timeout 10
```

The default UART settings are `115200 8N1` with no flow control.

Use the default `10 Hz` snapshot rate at `115200` baud. The readable JSON
snapshot is intentionally verbose; use a higher baud rate or a future binary
protocol before increasing the steady update rate substantially.

Only one process can normally own a Windows COM port. Close VS Code serial
monitors, ESP-IDF monitor, PuTTY, or other terminal applications before
starting the connector.

## Run With The Web GUI

The web GUI uses only the Python standard library. It can run with MSFS, with
debug data, with a UART-connected ESP32, or without a UART for desktop testing.

Debug GUI without ESP32 hardware:

```powershell
python -m gmc605_connector --web
```

The dashboard starts in Debug mode. Use its **Connector Source** selector to
switch between Debug, MSFS, and Auto while it remains open. Use the **ESP32
UART** controls to refresh and select from the visible detected-port list,
enter a port manually, connect, or disconnect without restarting the dashboard.
The **ESP32 Prints / UART RX** monitor displays raw lines printed or transmitted
by the ESP32. The **ESP32 Receives / UART TX** monitor displays JSON lines sent
by the connector to the ESP32. Port detection also reports when `pyserial` is
missing.

MSFS GUI with ESP32 on `COM5`:

```powershell
python -m gmc605_connector --web --mode msfs --port COM5
```

Open:

```text
http://127.0.0.1:8765
```

The GUI shows connector status, latest telemetry, AP mode fields, references,
raw protocol snapshots, and command buttons. In web mode, the server stays up
even if MSFS or the serial port is not ready yet; it retries and shows the last
connection error in the page log.

The web server starts before attempting SimConnect, so the dashboard remains
reachable even when SimConnect startup stalls.

## Run In Debug Mode

Debug mode sends mock snapshots over the real UART connection:

```powershell
python -m gmc605_connector --mode debug --port COM5
```

This allows the ESP32 input, UART parser, state snapshot, and OLED rendering to
be tested without MSFS.

For a short UART smoke test:

```powershell
python -m gmc605_connector --mode debug --port COM5 --snapshot-count 10
```

To inspect snapshots without an ESP32:

```powershell
python -m gmc605_connector --mode debug --transport stdout
```

The automated test suite uses pySerial's `loop://` URL transport to validate
the UART framing without physical hardware.

## Protocol

The first protocol is newline-delimited UTF-8 JSON. Each line is one complete
message. The `v` field is the protocol version.

The firmware-facing field reference and receive workflow are documented in
[`docs/workflows/esp32-connector-output-protocol.md`](../docs/workflows/esp32-connector-output-protocol.md).

Connector to ESP32 snapshot:

```json
{"v":1,"type":"snapshot","seq":42,"timestamp_ms":1780767726568,"source":"msfs","sim_connected":true,"ap":true,"fd":true,"yd":false,"lat_active":"HDG","lat_armed":"NONE","vert_active":"VS","vert_armed":["ALTS"],"nav_source":"GPS","cdi":{"valid":true,"needle":90,"half_scale":"GREATER"},"gsi":{"valid":false,"needle":0,"half_scale":"INVALID"},"references":{"heading_deg":270,"altitude_ft":5000,"vs_fpm":500,"speed_kt":120},"aircraft":{"heading_deg":250,"altitude_ft":3200,"vs_fpm":450,"airspeed_kt":118},"messages":[],"pending_commands":[]}
```

ESP32 to connector command request:

```json
{"v":1,"type":"command","seq":12,"command":"HDG_PRESS"}
```

Reference-setting command:

```json
{"v":1,"type":"command","seq":13,"command":"ALTITUDE_SET","value":6000}
```

The connector replies with a `command_result` message and then sends a new
snapshot. A successful command result means the request was transmitted or
applied in debug mode. The following snapshot remains the authoritative state.

## Supported Panel Commands

- `AP_PRESS`, `FD_PRESS`, `YD_PRESS`, `AP_DISCONNECT`
- `HDG_PRESS`, `NAV_PRESS`, `APR_PRESS`, `BC_PRESS`
- `ALT_PRESS`, `VS_PRESS`, `IAS_PRESS`, `FLC_PRESS`, `VNV_PRESS`
- `LVL_PRESS`, `GA_PRESS`
- `HEADING_SET`, `ALTITUDE_SET`, `VS_SET`, `SPEED_SET`

Generic MSFS events do not provide reliable GFC 600 behavior for every
aircraft. `LVL`, `GA`, `VNV`, advanced VNAV, and some Garmin-specific modes
will require an aircraft adapter or custom Input Events.

## Debug Commands

These commands are accepted only in debug mode and are intended to be sent by
the ESP32 or an automated UART test harness:

- `DEBUG_RESET`
- `DEBUG_SET_NAV_SOURCE` with `GPS`, `VOR`, `LOC`, or `NONE`
- `DEBUG_SET_CDI` with a value from `-127` to `127`
- `DEBUG_SET_GSI` with a value from `-127` to `127`
- `DEBUG_SET_SNAPSHOT` with a partial snapshot object
- `DEBUG_SET_SIMVARS` with raw SimVar-name keys to exercise the live derivation
- `DEBUG_CAPTURE_LATERAL`
- `DEBUG_CAPTURE_VERTICAL`

Example:

```json
{"v":1,"type":"command","seq":100,"command":"DEBUG_SET_NAV_SOURCE","value":"LOC"}
{"v":1,"type":"command","seq":101,"command":"DEBUG_SET_CDI","value":90}
{"v":1,"type":"command","seq":102,"command":"APR_PRESS"}
{"v":1,"type":"command","seq":103,"command":"DEBUG_CAPTURE_LATERAL"}
{"v":1,"type":"command","seq":104,"command":"DEBUG_CAPTURE_VERTICAL"}
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Current Limitations

- The baseline MSFS adapter uses generic SimVars and Key Events.
- Generic SimVars do not expose every Garmin-style armed or captured state.
- The generic adapter does not use the misleading `AUTOPILOT APPROACH ARM` or
  `AUTOPILOT GLIDESLOPE ARM` values as panel armed-state annunciations.
- Generic glideslope state can confirm LOC `GS`, but cannot prove GPS `GP`.
- GPS approach versus GPS navigation and LOC approach versus LOC navigation may
  require GP/GS state, command history, or an aircraft-specific adapter.
- Python-SimConnect is a third-party wrapper around the MSFS SimConnect API.
