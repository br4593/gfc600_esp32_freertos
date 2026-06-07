# Project Status

## Resume Here

The project is currently in the connector-model research and planning phase.

Next task:

1. Use the current output contract in
   [docs/workflows/esp32-connector-output-protocol.md](docs/workflows/esp32-connector-output-protocol.md)
   to plan the ESP32 UART parser and renderer.
2. Define the connector interfaces described in
   [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md):
   - `RawObservationFrame`
   - `CanonicalAfcsState`
   - `TransitionEvent`
3. Implement the remaining conservative generic SimVar mapping from
   [docs/MSFS_MAPPING.md](docs/MSFS_MAPPING.md).

## Current State

- The previous firmware and documentation were cleared.
- The Python connector is retained as the only implementation.
- Documentation was simplified into a logic reference, a concrete MSFS SimVar
  mapping, and one implementation/validation plan.
- The logic reference now includes hierarchical/parallel Mermaid state-machine
  drawings for engagement, lateral, vertical, protection, and attention logic.
- No ESP32 firmware currently exists.

## Completed Work

- Researched GFC 600 modes, captures, reversions, protection overrides, and GMC
  605 annunciations from Garmin Pilot's Guide `190-01488-00 Rev. H`.
- Established that the canonical AFCS model contains parallel regions:
  engagement, lateral active/armed, vertical active/armed, protection, and
  attention.
- Mapped generic MSFS autopilot SimVars to canonical modes with confidence
  levels and decision trees.
- Audited the connector's requested SimVars against the official MSFS SDK.
- Removed misleading generic approach/glideslope arm interpretations and stopped
  generic glideslope state from inventing GPS glidepath capture.
- Hardened debug overrides and added raw-SimVar debug simulation through the live
  derivation path.
- Documented the current ESP32-facing UART/JSON output protocol.
- Documented connector lifecycle fixes that prevent SimConnect startup/shutdown
  hangs.
- Added a simple interactive connector launch that asks for Debug or MSFS mode
  and selects the ESP32 serial port.
- Removed the firmware tree and old overlapping documentation.

## Key Technical Conclusions

The retained connector is a useful transport and debug prototype. Protocol V1
is now documented for initial ESP32 parser/rendering work, but it remains
provisional while the richer canonical model in
[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) is implemented.

- Missing/unavailable SimVars must remain unavailable, not become false.
- Startup, reconnect, and aircraft changes must create synchronization events,
  not false captures or reversions.
- Generic SimVars can represent many current modes but usually cannot prove
  transition reason, complete armed state, protection state, or failure cause.
- `FLC` is not a documented GMC 605 annunciation. It may map to canonical `IAS`
  only when an aircraft profile explicitly declares equivalence.
- The web GUI and future ESP32 must render explicit transition/attention intent;
  they must not infer it from label differences.

## Current Documentation

Read in this order:

1. [docs/GFC600_LOGIC.md](docs/GFC600_LOGIC.md) - canonical modes, state
   machines, transitions, and annunciations.
2. [docs/MSFS_MAPPING.md](docs/MSFS_MAPPING.md) - generic SimVar mapping,
   confidence, limitations, and aircraft-profile requirements.
3. [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) - implementation phases,
   deliverables, validation, and failure modes.
4. [docs/workflows/esp32-connector-output-protocol.md](docs/workflows/esp32-connector-output-protocol.md)
   - current firmware-facing transport and message contract.

## Open Decisions

- First target MSFS aircraft and simulator version.
- Exact Python types/interfaces for raw observations, canonical state, and
  transition events.
- Protocol V2 snapshot shape after connector mapping is validated; Protocol V1
  is documented for initial parser and renderer implementation.
- ESP32 board, display wiring, and serial-link details remain intentionally
  deferred.

## Current Plan

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

## Validation

- Official Garmin Pilot's Guide downloaded and extracted for mode/annunciation
  research.
- Firmware publishes every valid parsed snapshot through a length-one FreeRTOS
  display queue. The placeholder display-state task reports the link stale
  after 500 ms without a valid snapshot and reports recovery when snapshots
  resume.
- Connector test suite passes: 35 tests run, with the optional pySerial loopback
  test skipped because pySerial is not installed in the system Python environment.
- Current ESP-IDF firmware build passes. The generated application binary uses
  approximately 16% of the smallest application partition.
- Documentation validation passes: internal core-document links exist, Mermaid
  and Markdown code fences are balanced, and `git diff --check` is clean.

## Repository Notes

- Preserve `msfs_connector/`; it is the active implementation.
- Existing connector lifecycle changes are uncommitted and should not be lost.
- Loose LibreOffice lock files under `docs/` are ignored with `.~lock.*#`.
- The removed firmware and old docs appear as intentional deletions in Git.
