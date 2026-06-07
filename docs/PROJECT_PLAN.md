# Project Plan And Validation

## Goal

Build an MSFS-only physical GMC 605-style panel. MSFS owns actual autopilot
behavior. The connector maps MSFS state into the canonical modes defined in
[GFC600_LOGIC.md](GFC600_LOGIC.md). The future ESP32 renders snapshots and sends
semantic input requests.

## Ownership

| System | Responsibility |
|---|---|
| MSFS aircraft | Actual autopilot guidance and aircraft response. |
| Connector | SimConnect, aircraft mapping, canonical state, transition tracking, messages, and protocol. |
| Future ESP32 | Physical inputs, OLED/LED rendering, and link health. |

The ESP32 must not decide that a mode armed, captured, reverted, or failed.

## Phase 1: Generic Connector Mapping

Deliverables:

1. `RawObservationFrame`: one timestamped set of SimVars plus aircraft identity.
2. `CanonicalAfcsState`: engagement, active/armed axes, references, messages,
   profile capabilities, and per-field confidence.
3. `TransitionEvent`: changed axis, previous/new mode, reason, attention style,
   and expiry.
4. Conservative generic adapter implementing [MSFS_MAPPING.md](MSFS_MAPPING.md).
5. Web GUI rendering explicit transition/attention data instead of guessing from
   label changes.
6. Trace recorder and replay test fixture format.

Raw observation requirements:

- Preserve unavailable values as unavailable, never false.
- Assign a connection generation so reconnect/aircraft-change frames cannot be
  compared against stale prior state.
- Store conflicting simultaneous mode values for diagnostics.

Validation:

- AP/FD/YD and basic HDG/ALT/VS/IAS states map correctly.
- GPS/VOR/LOC mappings expose their confidence.
- Generic mapping does not invent GP, VNAV, protection, or failure causes.
- FLC is not displayed as a GFC mode unless a profile maps it to canonical IAS.
- Connector startup produces synchronization transitions, not false captures or
  reversions.
- Coupled mode updates are atomic across lateral and vertical axes.
- Missing SimVars do not create false disengagement or reversion events.
- Startup, reconnect, and aircraft changes create synchronization events only.

## Phase 2: First Aircraft Profile

1. Choose one target aircraft and simulator version.
2. Record timestamped raw SimVars while exercising every supported mode.
3. Inspect aircraft-specific Input Events or variables when generic data is
   insufficient.
4. Define supported capabilities and command mappings.
5. Replay recorded traces through automated tests.

Minimum trace set:

```text
00 cold/start synchronization
01 FD and AP engagement/disengagement
02 HDG, ALT, VS, IAS/FLC selections
03 NAV arm and capture
04 APR GPS/VOR/LOC arm and capture
05 BC arm and capture
06 selected-altitude capture
07 source/data-loss reversion
08 aircraft-specific capabilities
```

Validation scenarios:

- FD/AP engagement and default `ROL` + `PIT`.
- HDG, ALT, VS, and IAS selection/deselection.
- NAV/APR armed versus active behavior.
- GPS/VOR/LOC source changes and reversions.
- `ALTS`, GP/GS, VNAV, protections, and alerts only when confirmed.

## Phase 3: Stable Panel Protocol

Define one complete connector snapshot containing:

- Canonical active and armed modes.
- Relevant reference value.
- AP/FD/YD LED state and attention intent.
- Messages.
- Transition reason and attention expiry.
- Adapter identity and confidence.

Commands remain semantic requests. Only later snapshots confirm resulting state.

Protocol acceptance criteria:

- A renderer can reproduce all documented attention behavior without comparing
  snapshots to guess transition causes.
- Unknown state and unsupported capability are distinguishable.
- A newly connected renderer can synchronize without replaying stale alerts.
- Protocol messages remain bounded and versioned.

## Phase 4: ESP32

After the protocol is stable:

1. Implement OLED and AP/FD/YD indicator rendering.
2. Add link stale/lost indication.
3. Add button and encoder scanning.
4. Send semantic command requests.
5. Verify the ESP32 never reconstructs AFCS logic.

## Test Strategy

| Layer | Test method |
|---|---|
| Raw SimConnect collection | Recorded observation frames and missing-value tests. |
| Generic/profile mapping | Table-driven unit tests for every mapping priority. |
| Transition tracker | Replay traces for selection, capture, reversion, synchronization, and unknown changes. |
| Display projection | Golden snapshots for active/armed fields, references, messages, and attention. |
| Web GUI | Verify it renders explicit snapshot intent without local mode inference. |
| Future ESP32 | Protocol replay and link-loss tests before connecting to MSFS. |

## Important Failure Modes

- A stale or unavailable SimVar is interpreted as false and causes a fake
  reversion.
- Simultaneously true SimVars select the wrong mode because priority is wrong.
- A command is accepted by SimConnect but the aircraft ignores it.
- Startup state is mistaken for an automatic capture.
- Aircraft/profile change retains old armed modes or alert timers.
- Generic source mapping confuses LOC/VOR/GPS.
- Web GUI or ESP32 independently invents transition meaning.

## Current Next Step

Define the raw observation, canonical state, and transition-event interfaces,
then implement and replay-test the conservative generic mapping before restarting
firmware.
