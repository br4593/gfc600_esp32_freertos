# GFC 600 Mode-Key Behavior With FD And AP Off

## Goal

Define what the simulator panel should do when a mode key is pressed while the
Flight Director (FD), Autopilot (AP), or both are off.

This project is for Microsoft Flight Simulator only. The behavior below is a
simulator control and annunciation model, not real aircraft operating guidance.

## Sources Used

Primary GFC 600 sources:

- Garmin, `GFC 600 Automatic Flight Control System (with Color Display) Pilot's
  Guide`, `190-03090-00 Rev. A`, January 2024:
  https://static.garmin.com/pumac/190-03090-00_a.pdf
- Garmin, `GFC 600 Pilot's Guide`, `190-01488-00 Rev. H`:
  https://static.garmin.com/pumac/190-01488-00_h.pdf
- Garmin, `GFC 600 Autopilot Installed in Textron Aviation 525` AFMS,
  `190-02011-15 Rev. 1`:
  https://static.garmin.com/pumac/190-02011-15_01.pdf

Official Garmin cross-check:

- Garmin, `G5 Electronic Flight Instrument Pilot's Guide for Certified
  Aircraft`, `190-01112-12 Rev. L`. Its GMC 507 Flight Director Activation
  table explicitly lists the modes selected when a mode key is pressed while
  the FD is not active:
  https://static.garmin.com/pumac/190-01112-12_0l.pdf

## Confirmed GFC 600 Facts

- The FD provides pitch and roll commands that can be hand-flown or followed by
  the AP.
- Pressing the `FD` key while FD is off activates FD in the default `ROL` and
  `PIT` modes.
- Pressing the `AP` key while FD is off activates FD and AP in the default `ROL`
  and `PIT` modes.
- Pressing the `GA` button activates FD.
- Pressing the `LVL` key engages AP in Level Mode, or selects Level Mode if AP
  is already engaged.
- The FD key is disabled while AP is engaged.
- Mode keys select and deselect their respective modes. In the absence of a
  selected mode, the affected axis reverts to its default mode:
  - Lateral default: `ROL`
  - Vertical default: `PIT`
- NAV requires a valid VOR or LOC signal, or an active GPS course, before FD can
  enter Navigation Mode.
- AP follows active FD commands. Therefore, `AP_ON` with `FD_OFF` is not a valid
  normal runtime state.

## What The GFC 600 Guide Does Not Explicitly Tabulate

The GFC 600 pilot guides do not provide a complete table showing the result of
pressing every ordinary mode key while both FD and AP are off.

Official Garmin AFCS documentation for related controllers does provide such a
table. It shows that a valid ordinary mode-key press activates FD in the
selected mode for that axis and the default mode for the other axis.

The project adopts that behavior as a high-confidence Garmin-style inference.
It must remain a bench and MSFS integration test item because it is not stated
as a complete GFC 600 table in the primary guide.

## Project Behavior Decision

### Valid Runtime Combinations

| AP State | FD State | Valid? | Meaning |
|---|---|---|---|
| off | off | yes | No flight director guidance is selected. |
| off | on | yes | FD guidance is available for hand-flying. |
| on | on | yes | AP follows the active FD commands. |
| on | off | no | State manager must prevent or correct this combination. |

### Mode-Key Behavior When Both FD And AP Are Off

| Control Pressed | FD Result | AP Result | Lateral Result | Vertical Result |
|---|---|---|---|---|
| `FD` | on | off | `ROL` | `PIT` |
| `AP` | on | on | `ROL` | `PIT` |
| `LVL` | on | on | `LVL` | `LVL` |
| `GA` | on | off | `GA` | `GA` |
| `HDG` | on | off | `HDG` | `PIT` |
| `NAV` | on if selection is valid | off | selected source active or armed | `PIT` |
| `APR` | on if selection is valid | off | selected approach active or armed | `PIT`; arm `GP` or `GS` when supported |
| `BC` | on if selection is valid | off | `BC` active or armed | `PIT` |
| `ALT` | on | off | `ROL` | `ALT` |
| `VS` | on | off | `ROL` | `VS`; arm `ALTS` when available |
| `IAS` or `FLC` | on | off | `ROL` | selected speed mode; arm `ALTS` when available |
| `VNV` | on if a valid VNAV path exists | off | `ROL` | `PIT` active with `VPTH` armed |

### Mode-Key Behavior When FD Is On And AP Is Off

- The selected mode changes the FD commands.
- AP remains off.
- The pilot can hand-fly the displayed FD commands.
- Pressing the currently active mode key deselects that mode and returns the
  affected axis to its default mode.

Examples:

| Starting State | Control Pressed | Result |
|---|---|---|
| FD on, `ROL` / `PIT` | `HDG` | `HDG` / `PIT`, AP remains off |
| FD on, `HDG` / `PIT` | `HDG` | `ROL` / `PIT`, AP remains off |
| FD on, `HDG` / `PIT` | `VS` | `HDG` / `VS`, AP remains off |
| FD on, `HDG` / `VS` | `VS` | `HDG` / `PIT`, AP remains off |

### Mode-Key Behavior When AP Is On

- FD is necessarily on.
- Selecting a mode changes the FD commands and AP follows the new commands.
- Pressing `FD` does nothing because the FD key is disabled while AP is
  engaged.
- Pressing `AP` disconnects AP but should leave FD and its active modes
  available.

## Invalid Or Unavailable Mode Selection

If a mode key requires data that is not valid, the state manager should not
enter that mode.

Examples:

- `NAV` without a valid GPS course, VOR signal, or LOC signal
- `APR` without a valid approach navigation source
- `BC` without a valid LOC signal
- `VNV` without a valid VNAV path

For the first firmware version:

- Keep FD and AP state unchanged when the requested mode is unavailable.
- Keep the current active and armed modes unchanged.
- Emit a diagnostic event or log entry.
- Do not show `DISABLED KEY` unless the selected aircraft profile marks the
  function as unsupported or disabled.

## State Manager Rules

1. Maintain the invariant `AP_ON` implies `FD_ON`.
2. A successful ordinary mode selection while FD is off first enables FD.
3. When enabling FD through a lateral mode key, set vertical active mode to
   `PIT` if it is `NONE`.
4. When enabling FD through a vertical mode key, set lateral active mode to
   `ROL` if it is `NONE`.
5. `LVL` is special because it engages AP and sets both axes.
6. `GA` is special because it sets both axes but does not engage AP when AP was
   off.
7. A failed mode-selection request must not leave FD on with either active axis
   set to `NONE`.

## Recommended Tests

| Test | Initial State | Action | Expected Result |
|---|---|---|---|
| HDG activates FD | FD off, AP off | Press `HDG` | FD on, AP off, `HDG` / `PIT` |
| VS activates FD | FD off, AP off | Press `VS` | FD on, AP off, `ROL` / `VS` |
| NAV valid activation | FD off, AP off, valid GPS course | Press `NAV` | FD on, AP off, GPS active or armed, `PIT` |
| NAV invalid activation | FD off, AP off, no valid nav source | Press `NAV` | No state change; diagnostic emitted |
| LVL engagement | FD off, AP off | Press `LVL` | FD on, AP on, `LVL` / `LVL` |
| GA activation | FD off, AP off | Press `GA` | FD on, AP off, `GA` / `GA` |
| Active HDG deselection | FD on, AP off, `HDG` active | Press `HDG` | `ROL` active, AP remains off |
| FD key disabled | FD on, AP on | Press `FD` | No state change |

## Open Questions

- Verify ordinary mode-key activation behavior against the first target MSFS
  aircraft and any available GFC 600 installation-specific reference.
- Decide whether unavailable mode selections should create a user-facing
  message or only a diagnostic log.
- Confirm whether every target aircraft supports AP-coupled GA, while retaining
  the rule that GA does not engage AP from an off state.

