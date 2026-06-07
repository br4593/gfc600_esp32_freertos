# ESP32 Connector Output Protocol

## Purpose

This document defines the current Python connector output that the future ESP32
firmware must parse and render.

The project is for Microsoft Flight Simulator only. The connector owns MSFS
interpretation and autopilot-mode mapping. The ESP32 is a renderer and input
device; it must not invent armed, captured, reverted, or failed modes.

## Transport

| Property | Current value |
|---|---|
| Physical link | UART/USB serial selected by the host OS |
| Default UART | `115200 8N1`, no flow control |
| Encoding | ASCII-compatible UTF-8 JSON |
| Framing | One JSON object per line, terminated by `\n` |
| Protocol version | `v: 1` |
| Default snapshot rate | `10 Hz` |
| Message size | Variable; Protocol V1 has no formal maximum |

The connector sends a `hello` message once after opening the transport, then
sends periodic `snapshot` messages. Commands received from the ESP32 produce a
`command_result` followed by a fresh `snapshot`.

## Firmware Receive Workflow

1. Read bytes into a bounded line buffer.
2. Wait for `\n`; one line is one complete JSON message.
3. Reject an overlong line, discard through the next `\n`, and show a local link
   diagnostic.
4. Parse JSON and require `v == 1`.
5. Dispatch on `type`.
6. For `snapshot`, replace the complete rendered state atomically.
7. Track the last valid snapshot receive time for link-stale indication.

Do not update the display field-by-field while parsing. Parse into a new
snapshot structure, validate it, then swap it with the displayed snapshot.

For the first firmware parser, a `2048`-byte line buffer is a practical
provisional limit for the current bounded fields. Treat a larger line as a
protocol error. A formal maximum must be added before Protocol V1 is frozen.

## Connector-To-ESP32 Messages

### Hello

Sent once when the connector opens the serial transport.

```json
{"v":1,"type":"hello","role":"host_connector","source":"debug","update_hz":10.0}
```

| Field | Type | Meaning |
|---|---|---|
| `v` | integer | Protocol version; currently `1`. |
| `type` | string | Always `hello`. |
| `role` | string | Always `host_connector`. |
| `source` | string | Initial source: `msfs`, `debug`, or `auto`. |
| `update_hz` | number | Configured periodic snapshot rate. |

The `source` in each snapshot is authoritative because auto mode can resolve to
either MSFS or debug.

### Snapshot

```json
{"v":1,"type":"snapshot","seq":42,"timestamp_ms":1780767726568,"source":"msfs","sim_connected":true,"ap":true,"fd":true,"yd":false,"lat_active":"HDG","lat_armed":"NONE","vert_active":"VS","vert_armed":["ALTS"],"nav_source":"GPS","cdi":{"valid":true,"needle":90,"half_scale":"GREATER"},"gsi":{"valid":false,"needle":0,"half_scale":"INVALID"},"references":{"heading_deg":270,"altitude_ft":5000,"vs_fpm":500,"speed_kt":120},"aircraft":{"heading_deg":250,"altitude_ft":3200,"vs_fpm":450,"airspeed_kt":118},"messages":[],"pending_commands":[]}
```

#### Envelope And Link Fields

| Field | Type | Meaning |
|---|---|---|
| `v` | integer | Protocol version. |
| `type` | string | Always `snapshot`. |
| `seq` | integer | Connector snapshot sequence; increases for every sent snapshot. |
| `timestamp_ms` | integer | Host Unix epoch time in milliseconds. Diagnostic only. |
| `source` | string | `msfs` for live SimConnect data or `debug` for simulated data. |
| `sim_connected` | boolean | Whether the snapshot represents a simulated/available MSFS connection. |

Use local receive time, not `timestamp_ms`, to detect a stale UART link. Host and
ESP32 clocks are not synchronized.

#### Engagement Fields

| Field | Type | Meaning |
|---|---|---|
| `ap` | boolean | Autopilot engaged LED state. |
| `fd` | boolean | Flight director enabled LED state. |
| `yd` | boolean | Yaw damper engaged LED state. |

The connector maintains the invariant that `ap: true` implies `fd: true`.

#### Mode Fields

| Field | Type | Current values |
|---|---|---|
| `lat_active` | string | `NONE`, `ROL`, `HDG`, `GPS`, `VOR`, `LOC`, `VAPP`, `BC`, `LVL`, `GA` |
| `lat_armed` | string | Same lateral labels; generic MSFS mode normally reports `NONE` because generic SimVars do not reliably expose lateral armed state. |
| `vert_active` | string | `NONE`, `PIT`, `ALT`, `ALTS`, `VS`, `IAS`, `FLC`, `VPTH`, `ALTV`, `GP`, `GS`, `LVL`, `GA` |
| `vert_armed` | array of strings | Zero or more of `ALT`, `ALTS`, `VPTH`, `ALTV`, `GP`, `GS`. |
| `nav_source` | string | `NONE`, `GPS`, `VOR`, or `LOC`. |

`FLC` remains in protocol version 1 for connector compatibility, but it is not a
documented GMC 605 annunciation. Firmware should support rendering it as an
unknown/compatibility label until an aircraft profile maps it to canonical
`IAS`.

Unknown future labels must not crash the firmware. Render a short fallback such
as `?` and preserve link operation.

#### Deviation Fields

Both `cdi` and `gsi` use the same protocol structure:

| Field | Type | Meaning |
|---|---|---|
| `valid` | boolean | Whether the deviation can be used. |
| `needle` | integer | Normalized signed deflection from `-127` to `127`. |
| `half_scale` | string | `LESS`, `GREATER`, or `INVALID`. |

`0` is centered. The sign indicates opposite sides of center; determine the
desired screen direction during display integration. The connector normalizes
MSFS GSI's native `-119..119` range into the protocol's `-127..127` range.

When `valid` is false, ignore `needle` and `half_scale` for flight-display
purposes.

#### Reference And Aircraft Fields

| Object.field | Type | Unit |
|---|---|---|
| `references.heading_deg` | integer | magnetic degrees, normalized `0..359` |
| `references.altitude_ft` | integer | feet |
| `references.vs_fpm` | integer | feet per minute |
| `references.speed_kt` | integer | knots |
| `aircraft.heading_deg` | integer | magnetic degrees, normalized `0..359` |
| `aircraft.altitude_ft` | integer | indicated feet |
| `aircraft.vs_fpm` | integer | feet per minute |
| `aircraft.airspeed_kt` | integer | indicated knots |

#### Message Fields

| Field | Type | Current limit | Meaning |
|---|---|---:|---|
| `messages` | array of strings | 4 entries, 32 characters each | Connector/display messages. |
| `pending_commands` | array of strings | 8 entries, 32 characters each | Reserved for connector command-state display. |

### Command Result

```json
{"v":1,"type":"command_result","command_seq":12,"command":"HDG_PRESS","accepted":true,"message":"transmitted AP_HDG_HOLD_ON"}
```

`accepted: true` means the connector accepted/applied or transmitted the request.
It does not prove the MSFS aircraft changed mode. The following snapshot is the
authoritative display state.

### Error

```json
{"v":1,"type":"error","message":"invalid JSON message: ..."}
```

An error reports a connector or received-message problem. It does not replace
the last valid snapshot.

## ESP32-To-Connector Commands

Command framing uses the same newline-delimited JSON format:

```json
{"v":1,"type":"command","seq":12,"command":"HDG_PRESS"}
{"v":1,"type":"command","seq":13,"command":"ALTITUDE_SET","value":6000}
```

| Field | Type | Meaning |
|---|---|---|
| `seq` | integer | ESP32-owned command sequence used to match `command_result.command_seq`. |
| `command` | string | Semantic button/encoder request. |
| `value` | number/string/object | Required only by commands that take a value. |

Panel commands:

```text
AP_PRESS FD_PRESS YD_PRESS AP_DISCONNECT
HDG_PRESS NAV_PRESS APR_PRESS BC_PRESS
ALT_PRESS VS_PRESS IAS_PRESS FLC_PRESS VNV_PRESS LVL_PRESS GA_PRESS
HEADING_SET ALTITUDE_SET VS_SET SPEED_SET
```

The ESP32 must send semantic requests and wait for snapshots. It must not change
the rendered autopilot state optimistically after sending a command.

## Debug Mode

Debug mode uses the exact same `hello`, `snapshot`, `command_result`, and `error`
message shapes as live mode. It exists to test UART parsing, input handling, and
display rendering without MSFS.

Run a finite stdout simulation:

```bash
cd msfs_connector
PYTHONPATH=src python -m gmc605_connector --mode debug --transport stdout --snapshot-count 3
```

Debug-only commands:

```text
DEBUG_RESET
DEBUG_SET_NAV_SOURCE
DEBUG_SET_CDI
DEBUG_SET_GSI
DEBUG_SET_SNAPSHOT
DEBUG_SET_SIMVARS
DEBUG_CAPTURE_LATERAL
DEBUG_CAPTURE_VERTICAL
```

`DEBUG_SET_SNAPSHOT` applies a partial snapshot atomically. Invalid field types
or labels reject the whole command and leave the previous snapshot unchanged.
Debug snapshots enforce live-output invariants such as AP implying FD.

`DEBUG_SET_SIMVARS` accepts an object containing raw SimVar-name keys and passes
it through the same `derive_snapshot()` function as live MSFS mode. Use it when
testing the exact generic adapter output. `DEBUG_SET_SNAPSHOT` intentionally
supports richer aircraft-adapter/display scenarios that generic SimVars cannot
prove.

## Generic MSFS Mapping Limits

The current generic adapter intentionally does not invent data that the MSFS SDK
cannot prove:

- `AUTOPILOT APPROACH ARM` is not used as lateral armed state.
- `AUTOPILOT GLIDESLOPE ARM` is not used as vertical armed state.
- Generic glideslope state can produce active `GS` only with a LOC source; it
  cannot prove GPS `GP`.
- Generic lateral armed mode and GP/GS armed state require an aircraft adapter
  or command-history mapping.
- Reference slot indices and unavailable-versus-false SimVars still require a
  future protocol/model revision.

The ESP32 must display the connector's state as received. It must not infer a
missing `GP`, `GS`, `LOC`, or other mode from CDI/GSI position.

## Firmware Acceptance Checklist

- Parses fragmented and combined UART reads.
- Rejects invalid JSON, wrong protocol version, and overlong lines.
- Atomically swaps validated snapshots.
- Handles every listed mode label plus unknown labels.
- Treats deviation as invalid when `valid` is false.
- Uses local receive time for stale/lost-link detection.
- Matches command results by command sequence.
- Does not treat command acceptance as mode confirmation.
- Does not infer autopilot logic from aircraft or deviation fields.

## Sources

- Connector implementation:
  `msfs_connector/src/gmc605_connector/model.py`,
  `protocol.py`, `connector.py`, `transport.py`, `msfs_source.py`, and
  `debug_source.py`
- MSFS Aircraft Autopilot/Assistant Variables:
  https://docs.flightsimulator.com/html/Programming_Tools/SimVars/Aircraft_SimVars/Aircraft_AutopilotAssistant_Variables.htm
- MSFS Aircraft Radio Navigation Variables:
  https://docs.flightsimulator.com/html/Programming_Tools/SimVars/Aircraft_SimVars/Aircraft_RadioNavigation_Variables.htm
- MSFS Autopilot/Flight Assist Events:
  https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Autopilot_Flight_Assist_Events.htm
