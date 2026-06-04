# GFC 600 Mode Logic

## Goal

Define the complete GFC 600-style mode model for the MSFS-only ESP32 panel:

- available states
- active and armed mode rules
- button selection behavior
- capture, deselection, reversion, and protection transitions
- implementation priorities and unresolved questions

This is the single authoritative project document for mode behavior. It
describes simulator control and annunciation state, not real aircraft autopilot
guidance.

## Sources Used

Primary GFC 600 source:

- Garmin, `GFC 600 Automatic Flight Control System (with Color Display) Pilot's
  Guide`, `190-03090-00 Rev. A`, January 2024:
  https://static.garmin.com/pumac/190-03090-00_a.pdf

Additional official Garmin sources:

- Garmin, `GFC 600 Pilot's Guide`, `190-01488-00 Rev. H`:
  https://static.garmin.com/pumac/190-01488-00_h.pdf
- Garmin, `GFC 600 Autopilot Installed in Textron Aviation 525` AFMS,
  `190-02011-15 Rev. 1`:
  https://static.garmin.com/pumac/190-02011-15_01.pdf
- Garmin, `G5 Electronic Flight Instrument Pilot's Guide for Certified
  Aircraft`, `190-01112-12 Rev. L`. The GMC 507 Flight Director Activation
  table is used only as an official Garmin cross-check where the GFC 600 guide
  does not provide an equivalent table:
  https://static.garmin.com/pumac/190-01112-12_0l.pdf

Related project documents:

- [GFC 600 Mode Logic Test Plan](../test-plans/gfc600-mode-logic-test-plan.md)
- [MSFS SimVar And Event Map](../research/msfs-gmc605-simvar-event-map.md)
- [GMC 605 Firmware Architecture](../design-decisions/gmc605-firmware-architecture.md)

Relevant printed pages in `190-03090-00 Rev. A`:

| Topic | Printed Pages |
|---|---|
| Controls, alternate-action keys, AP/FD defaults, and invalid-data reversion | 14-15, 22-23 |
| Overspeed and underspeed protection | 35-39 |
| Vertical modes, altitude capture, GP/GS, and VNAV | 41-57 |
| Heading, NAV, APR, and BC modes | 61-70 |

## Confidence Labels

| Label | Meaning |
|---|---|
| Confirmed | Directly stated or clearly shown in the GFC 600 color-display guide. |
| Derived | Follows from confirmed GFC 600 alternate-action or mode-validity rules, but the exact full transition is not tabulated. |
| Garmin cross-check | Explicitly documented for another Garmin AFCS controller and adopted as a project rule pending MSFS bench testing. |
| Installation-dependent | Depends on installed PFD, HSI/DG, navigator, airframe, or aircraft profile. |

## Terms Used In The Tables

- `unchanged` means preserve the current value.
- `none` means no mode in that state group.
- Armed vertical modes are written as a set, for example `{ALTS, GP}`.
- `selected NAV` means the Navigation mode matching the selected source:
  `GPS_NAV`, `VOR_NAV`, or `LOC_NAV`.
- `selected APR` means the Approach mode matching the selected source:
  `GPS_APR`, `VOR_APR`, or `LOC_APR`.
- The renderer may show the same label for different internal modes:

| Internal Semantic Mode | Display Label |
|---|---|
| `GPS_NAV` | `GPS` |
| `GPS_APR` | `GPS` |
| `VOR_NAV` | `VOR` |
| `VOR_APR` | `VAPP` |
| `LOC_NAV` | `LOC` |
| `LOC_APR` | `LOC` |

## State Model Catalog

The firmware should not use one large enum for the whole system. These state
groups exist at the same time, and only the state manager should modify the
writable state instance.

### Primary Mode States

| Group | Allowed States | Notes |
|---|---|---|
| Flight director | `OFF`, `ON` | AP cannot normally be on while FD is off. |
| Autopilot | `OFF`, `ON`, manual disconnect, automatic disconnect, fail | Disconnect and failure states also drive alerts. |
| Yaw damper | `OFF`, `ON`, manual disconnect, fail | Installation-dependent. |
| Active lateral | `NONE`, `ROL`, `HDG`, `GPS_NAV`, `GPS_APR`, `VOR_NAV`, `VOR_APR`, `LOC_NAV`, `LOC_APR`, `BC`, `LVL`, `GA` | Exactly one while FD is on. |
| Armed lateral | `NONE`, `GPS_NAV`, `GPS_APR`, `VOR_NAV`, `VOR_APR`, `LOC_NAV`, `LOC_APR`, `BC` | Zero or one capture target. |
| Active vertical | `NONE`, `PIT`, `ALT`, `ALTS`, `VS`, `IAS`, `FLC`, `VPTH`, `ALTV`, `GP`, `GS`, `LVL`, `GA` | Exactly one while FD is on. |
| Armed vertical set | `ALTS`, `ALT`, `VPTH`, `ALTV`, `GP`, `GS` | Zero or more compatible capture targets. |
| Navigation source | `NONE`, `GPS`, `VOR`, `LOC` | Input used to interpret NAV and APR requests. |

The selected panel profile decides whether the user-facing speed mode is `IAS`
or `FLC`.

### Supporting State Groups

| Group | Allowed States Or Examples | Purpose |
|---|---|---|
| System lifecycle | boot, preflight test, ready, fail | Firmware startup and health. |
| Guidance modifiers | track mode, Smart Glide, low bank | Modify guidance or display without replacing the normal active mode. |
| CWS | released, held | Held control condition, not a mode. |
| Emergency Descent Mode | off, armed, delay, active, inhibited, overridden | Optional coordinated feature. |
| Protection | none, `MINSPEED`, `MAXSPEED` | Explains automatic protection transitions. |
| ESP | enabled, disabled, active, fail | Optional feature. |
| Smart Rudder Bias | off, armed, active left engine, active right engine, fail | Optional feature. |
| Trim and sensor health | trim OK/fail, mistrim direction, air-data OK/fail, attitude OK/fail | Alerts and mode availability. |
| Link and simulator | link OK/stale/lost, simulator connected/disconnected | Panel and host health. |
| Display effects | steady, slow flash, fast flash, inverse flash | Rendering metadata, not mode state. |

References such as selected heading, selected altitude, selected vertical speed,
selected IAS/FLC speed, pitch reference, CDI, and vertical deviation are data,
not mode states. Messages such as `PFT`, `LINK`, `SIM`, `SET HDG=CRS`,
`DISABLED KEY`, and trim or sensor failures are display output, not lateral or
vertical modes.

## Required State-Model Rules

1. `AP_ON` implies `FD_ON`.
2. While FD is on, exactly one lateral mode and one vertical mode are active.
3. The default lateral mode is `ROL`; the default vertical mode is `PIT`.
4. Normal mode keys are alternate action: press once to select, press again to
   deselect.
5. Lateral and vertical modes are normally selected independently.
6. Internal lateral state must distinguish NAV from APR even when the visible
   label is the same. The `NAV` key can cancel `GP` or `GS` while leaving a
   visible `GPS` or `LOC` lateral label.
7. Armed vertical modes must be represented as a set, not one enum value. The
   guide shows `VPTH` active while `ALTV` and `GP` are both armed.
8. Protection modes need separate suspended-mode storage. A mode temporarily
   shown as armed during `MINSPEED` or `MAXSPEED` is a restore target, not
   necessarily a normal capture-armed selection.

## Mode Availability And Capture Preconditions

| Mode Or Event | Preconditions | Result When Preconditions Are Not Met | Confidence |
|---|---|---|---|
| `NAV` | Valid VOR or LOC signal, or active GPS course | Do not enter Navigation mode | Confirmed |
| `APR` | Valid VOR or LOC signal, or active GPS course appropriate to the approach | Do not enter Approach mode | Confirmed |
| `BC` | Valid localizer backcourse data | Do not enter Backcourse mode | Derived |
| `VNV` | GPS flight plan with vertical constraints, GPS selected, and selected altitude set for the descent | Do not arm `VPTH` | Confirmed |
| `ALTS` | Selected-altitude capture available from a Garmin PFD interface | Do not arm or show `ALTS` | Installation-dependent |
| NAV/APR/BC arming | HSI-style interface and CDI greater than half scale | A DG installation cannot arm; align below half scale and force capture | Confirmed |
| `LOC_APR` capture | Localizer intercept geometry valid | Capture is inhibited when heading differs from localizer course by more than 105 degrees | Confirmed |
| `GP` capture | GPS active lateral, valid vertical deviation, CDI less than full scale, and waypoint sequencing not suspended | Remain armed | Confirmed |
| `GS` capture | `LOC_APR` is active | Remain armed until localizer capture | Confirmed |

For the first firmware version, an unavailable selection should leave FD, AP,
and mode state unchanged and create a diagnostic record. `DISABLED KEY` should
be reserved for a function that the selected installation profile does not
support.

## Engagement And Status Events

| Event And Starting Condition | FD After | AP After | Active Lateral After | Armed Lateral After | Active Vertical After | Armed Vertical After | Confidence |
|---|---|---|---|---|---|---|---|
| `FD_PRESS`, FD off | on | unchanged/off | `ROL` | none | `PIT` | `{ALTS}` if available | Confirmed |
| `FD_PRESS`, FD on and AP off | off | off | none | none | none | none | Confirmed; clearing modes is the project representation of FD deactivation |
| `FD_PRESS`, AP on | on | on | unchanged | unchanged | unchanged | unchanged | Confirmed; FD key is disabled |
| `AP_PRESS`, FD off and AP off | on | on | `ROL` | none | `PIT` | `{ALTS}` if available | Confirmed |
| `AP_PRESS`, FD on and AP off | on | on | unchanged | unchanged | unchanged | unchanged | Confirmed |
| `AP_PRESS` or `AP_DISCONNECT`, AP on | on by default | off/disconnect alert | unchanged | unchanged | unchanged | unchanged | Derived for command-bar installations; no-command-bars exception is confirmed |
| AP disconnect in a profile without command bars | off | off/disconnect alert | none | none | none | none | Installation-dependent |
| `LVL_PRESS` | on | on | `LVL` | none | `LVL` | none | Confirmed |
| `GA_PRESS` | on | unchanged | `GA` | none | `GA` | `{ALTS}` if available | Confirmed; replacing prior armed modes is derived |

### Mode Selection While FD And AP Are Off

The GFC 600 guide does not provide a complete table for every ordinary mode key
while FD is off. The project adopts the explicit Garmin GMC 507 activation
table as a high-confidence cross-check.

| Control Pressed | FD After | AP After | Lateral Result | Vertical Result |
|---|---|---|---|---|
| `HDG` | on | off | `HDG` | `PIT` |
| `NAV` | on if valid | off | selected NAV active or armed | `PIT` |
| `APR` | on if valid | off | selected APR active or armed | `PIT`; add `GP` or `GS` when supported |
| `BC` | on if valid | off | `BC` active or armed | `PIT` |
| `ALT` | on | off | `ROL` | `ALT` |
| `VS` | on | off | `ROL` | `VS`; add `ALTS` when available |
| `IAS` or `FLC` | on | off | `ROL` | selected speed mode; add `ALTS` when available |
| `VNV` | on if valid | off | `ROL` | `PIT` active with `VPTH` armed |

An invalid `NAV`, `APR`, `BC`, or `VNV` request leaves FD, AP, and mode state
unchanged and creates a diagnostic record.

## General Mode-Key Rules

| Event | Result | Confidence |
|---|---|---|
| Valid ordinary lateral key pressed while FD is off | Enable FD, select or arm the requested lateral mode, and use `PIT` on the vertical axis | Garmin cross-check |
| Valid ordinary vertical key pressed while FD is off | Enable FD, select or arm the requested vertical mode, and use `ROL` on the lateral axis | Garmin cross-check |
| Key for the currently active mode pressed | Deselect that mode and revert the affected axis to `ROL` or `PIT` | Confirmed |
| Key for a mode that is armed but not active pressed | Disarm that mode and leave the current active mode unchanged | Derived |
| Armed mode meets capture criteria | Move the armed mode to active and flash its active annunciation for 10 seconds | Confirmed |
| One-axis mode is selected | Change only that axis unless a coupled-mode or invalidation rule says otherwise | Confirmed |
| Required data for an active mode becomes invalid | Revert the affected axis to its default and flash the dropped mode in yellow | Confirmed |

Do not globally clear armed modes whenever an active mode changes. Valid
combinations include `HDG` active with NAV or APR armed, and `VPTH` active with
both `ALTV` and `GP` armed. Clear an armed mode when its own selection is
deselected, a conflicting selection replaces it, `LVL` or `GA` replaces the
mode set, or its required data becomes invalid.

## Lateral Selection And Capture Events

### Roll Hold Behavior

| Bank Angle When `ROL` Activates | Command |
|---|---|
| Less than 6 degrees | Roll wings level. |
| 6 to 25 degrees | Maintain the current bank angle. |
| More than 25 degrees | Limit the commanded bank to 25 degrees. |

When `ROL` is entered because of a mode reversion, the command is wings level.

| Event And Condition | Active Lateral After | Armed Lateral After | Vertical Effect | Confidence |
|---|---|---|---|---|
| `HDG_PRESS`, `HDG` not active | `HDG` | Preserve compatible armed capture mode | unchanged | Confirmed; armed preservation is a project rule |
| `HDG_PRESS`, `HDG` active | `ROL` | Preserve compatible armed capture mode | unchanged | Confirmed; armed preservation is a project rule |
| `NAV_PRESS`, valid source, CDI greater than half scale, arm-capable interface | unchanged | selected NAV | unchanged | Confirmed |
| `NAV_PRESS`, valid source, CDI less than half scale | selected NAV | none | unchanged | Confirmed |
| `NAV_PRESS`, DG interface, CDI greater than half scale | unchanged | unchanged | unchanged | Confirmed; NAV cannot arm |
| `NAV_PRESS`, selected NAV already armed | unchanged | none | unchanged | Derived |
| `NAV_PRESS`, selected NAV already active | `ROL` | none | unchanged | Confirmed alternate-action rule |
| `NAV_PRESS`, selected APR active | corresponding NAV mode | none | Cancel associated `GP` or `GS` for GPS/LOC; if it was active, vertical reverts to `PIT` | GP/GS cancellation confirmed; complete transition derived |
| `NAV_PRESS`, selected APR armed | unchanged | corresponding NAV mode | Cancel associated `GP` or `GS` for GPS/LOC | GP/GS cancellation confirmed; complete transition derived |
| `APR_PRESS`, valid source, CDI greater than half scale, arm-capable interface | unchanged | selected APR | Add `GP` for GPS or `GS` for LOC | Confirmed |
| `APR_PRESS`, valid source, CDI less than half scale | selected APR | none | Add `GP` for GPS or `GS` for LOC | Confirmed |
| `APR_PRESS`, selected APR already armed | unchanged | none | Remove associated `GP` or `GS` | Derived |
| `APR_PRESS`, selected APR already active | `ROL` | none | Remove associated `GP` or `GS`; if it was active, vertical reverts to `PIT` | Derived |
| `BC_PRESS`, valid signal, CDI greater than half scale, arm-capable interface | unchanged | `BC` | unchanged | Confirmed |
| `BC_PRESS`, valid signal, CDI less than half scale | `BC` | none | unchanged | Confirmed |
| `BC_PRESS`, `BC` already armed | unchanged | none | unchanged | Derived |
| `BC_PRESS`, `BC` already active | `ROL` | none | unchanged | Confirmed alternate-action rule |
| Lateral capture criteria met | previously armed NAV, APR, or BC mode | none | unchanged | Confirmed |
| `LOC_APR` armed, heading difference greater than 105 degrees | unchanged | `LOC_APR` remains armed | `GS` remains armed if valid | Confirmed |
| Active NAV/APR source changes or required signal/frequency becomes invalid | `ROL` with wings-level command | none | Evaluate associated `GP` or `GS`; revert vertical to `PIT` if its data is invalid | Confirmed; associated vertical cleanup is derived |
| Magnetic heading is lost in a supported TXi installation | Project model preserves the normal lateral label and activates the `TRACK MODE` modifier | unchanged | unchanged | Installation-dependent; modifier representation is a project rule |

### NAV And APR Semantic Conversion

The visible label is not enough to decide what the next key press means.

| Starting Semantic Mode | Event | Semantic Mode After | Visible Label After | Vertical Effect |
|---|---|---|---|---|
| `GPS_NAV` active or armed | `APR_PRESS` | `GPS_APR` active or armed | `GPS` | Arm `GP` |
| `GPS_APR` active or armed | `NAV_PRESS` | `GPS_NAV` active or armed | `GPS` | Cancel `GP` |
| `LOC_NAV` active or armed | `APR_PRESS` | `LOC_APR` active or armed | `LOC` | Arm `GS` |
| `LOC_APR` active or armed | `NAV_PRESS` | `LOC_NAV` active or armed | `LOC` | Cancel `GS` |
| `VOR_NAV` active or armed | `APR_PRESS` | `VOR_APR` active or armed | `VAPP` | none |
| `VOR_APR` active or armed | `NAV_PRESS` | `VOR_NAV` active or armed | `VOR` | none |

The GFC 600 guide directly states that the NAV key cancels `GP` when GPS is
active or armed and cancels `GS` when LOC is active or armed. The semantic
conversion model is the project representation of that behavior.

## Vertical Selection And Capture Events

| Event And Condition | Active Vertical After | Armed Vertical Set After | Lateral Effect | Confidence |
|---|---|---|---|---|
| FD or AP default activation | `PIT` | Add `ALTS` if available | `ROL` when no lateral mode already exists | Confirmed |
| `ALT_PRESS`, `ALT` not active | `ALT` | Remove `ALTS` and `ALT`; preserve compatible approach/VNAV arms | unchanged | Confirmed; preservation rule is a project rule |
| `ALT_PRESS`, `ALT` active | `PIT` | Add `ALTS` if available; preserve compatible approach/VNAV arms | unchanged | Confirmed alternate-action rule |
| `VS_PRESS`, `VS` not active | `VS` | Add `ALTS` if available; preserve compatible approach/VNAV arms | unchanged | Confirmed |
| `VS_PRESS`, `VS` active | `PIT` | Add `ALTS` if available; preserve compatible approach/VNAV arms | unchanged | Confirmed alternate-action rule |
| `IAS_PRESS` or `FLC_PRESS`, selected speed mode not active | `IAS` or `FLC` | Add `ALTS` if available; preserve compatible approach/VNAV arms | unchanged | Confirmed |
| `IAS_PRESS` or `FLC_PRESS`, selected speed mode active | `PIT` | Add `ALTS` if available; preserve compatible approach/VNAV arms | unchanged | Confirmed alternate-action rule |
| `VNV_PRESS`, valid VNAV path, VNV not selected | unchanged | Add `VPTH`; add `ALTV` when descending toward a vertical-path constraint | unchanged | Confirmed |
| `VNV_PRESS`, `VPTH` armed | unchanged | Remove `VPTH` and `ALTV` | unchanged | Derived |
| `VNV_PRESS`, `VPTH` or `ALTV` active | `PIT` | Remove `VPTH` and `ALTV`; preserve compatible approach arms | unchanged | Derived |
| VNAV path capture | `VPTH` | Remove `VPTH`; `ALTV`, `GP`, or `GS` may remain armed | unchanged | Confirmed |
| Another vertical mode selected while VNAV remains selected | selected vertical mode | Add or retain `VPTH` | unchanged | Garmin cross-check; project rule |
| Descending toward VNAV constraint while `VPTH` armed or active | unchanged | Add `ALTV` | unchanged | Confirmed |
| VNAV constraint capture | `ALTV` | Remove `ALTV`; retain other compatible arms | unchanged | Confirmed; post-capture sequence is profile-dependent |
| GPS `APR_PRESS` | unchanged | Add `GP` | GPS APR becomes active or armed | Confirmed |
| LOC `APR_PRESS` | unchanged | Add `GS` | LOC APR becomes active or armed | Confirmed |
| Glidepath capture criteria met | `GP` | Remove `GP`, `ALTS`, `ALTV`, and `VPTH` | `GPS_APR` must be active | Confirmed; incompatible-arm cleanup is derived |
| Glideslope capture criteria met | `GS` | Remove `GS`, `ALTS`, `ALTV`, and `VPTH` | `LOC_APR` must be active | Confirmed; incompatible-arm cleanup is derived |
| Selected altitude capture starts | `ALTS` | Remove `ALTS`, add `ALT` | unchanged | Confirmed |
| Aircraft reaches 50 feet from selected altitude | `ALT` | Remove `ALT` | unchanged | Confirmed |
| Selected altitude changes while `ALTS` is active | `PIT` | Add `ALTS` for the new selected altitude | unchanged | Confirmed |
| `CWS` held and released while `GP` or `GS` is active | `GP` or `GS` remains active | unchanged | unchanged | Confirmed |
| `GA` attitude is modified with CWS or NOSE UP/DN wheel | `PIT` | Add `ALTS` if available | `ROL` | Confirmed |

## Coupled Mode Events

| Event | Active Lateral After | Armed Lateral After | Active Vertical After | Armed Vertical After | Notes |
|---|---|---|---|---|---|
| `LVL_PRESS` | `LVL` | none | `LVL` | none | Engages AP if needed and cancels all prior active and armed modes. |
| `GA_PRESS` | `GA` | none | `GA` | `{ALTS}` if available | FD activates; AP remains in its previous engagement state. |
| One-axis mode selected while `LVL` or `GA` is active | Selected mode on that axis | As required by selection | Other axis remains `LVL` or `GA` until separately changed | As required by selection | Project rule based on normal independent-axis selection; verify in MSFS. |
| CWS or NOSE UP/DN wheel modifies GA attitude | `ROL` | none | `PIT` | `{ALTS}` if available | Confirmed GA reversion. |

## Automatic Reversion And Protection Events

| Event And Condition | Active Lateral After | Armed/Suspended Lateral | Active Vertical After | Armed/Suspended Vertical | Confidence |
|---|---|---|---|---|---|
| Required data for active lateral mode becomes invalid | `ROL` with wings-level command | none | unchanged | unchanged | Confirmed |
| Required data for active vertical mode becomes invalid | unchanged | unchanged | `PIT` | none for the invalid mode | Confirmed |
| Attitude data required for default modes becomes invalid | none; FD disabled | none | none; FD disabled | none | Confirmed |
| Overspeed protection enters while `PIT`, `VS`, `IAS`, `FLC`, or `ALTS` is active | unchanged | unchanged | `IAS` or `FLC` | Suspend the previous active vertical mode and show it armed | Confirmed |
| Overspeed condition clears | unchanged | unchanged | Restore the suspended vertical mode | Clear suspended vertical restore target | Confirmed |
| Underspeed enters from altitude-critical `ALT`, `GS`, `GP`, or `GA` with AP on | `ROL` | Suspend the previous active lateral mode and show it armed | `IAS` or `FLC` | Suspend the previous active vertical mode and show it armed | Confirmed; airframe-dependent trigger |
| Altitude-critical underspeed clears at minimum speed plus 5 KIAS | Restore suspended lateral mode | Clear restore target | Restore suspended vertical mode | Clear restore target | Confirmed |
| Underspeed enters from non-altitude-critical `VS`, `LVL`, `PIT`, `IAS`, `ALTS`, or VNAV with AP on | unchanged | unchanged | `IAS` or `FLC` | Suspend the previous active vertical mode and show it armed | Confirmed; airframe-dependent trigger |
| Non-altitude-critical underspeed clears at minimum speed plus 5 KIAS | unchanged | unchanged | Restore suspended vertical mode | Clear restore target | Confirmed |
| GA was active before underspeed and NOSE UP/DN wheel is moved during protection | Restore lateral as specified by protection exit | Clear restore target | `PIT` after protection exit | Add `ALTS` if available | Confirmed |
| Emergency Descent Mode activates, if configured | `HDG` | profile-dependent | `FLC` | profile-dependent | Installation-dependent; also commands descent references and selected altitude. |

Overspeed protection is not active in `ALT`, `GS`, `GP`, or `GA`.

## Recommended Firmware Event Groups

The state manager should receive events, not raw button GPIO state or raw MSFS
variables.

| Event Group | Examples | State Manager Responsibility |
|---|---|---|
| Selection requests | `FD_PRESS`, `AP_PRESS`, `HDG_PRESS`, `NAV_PRESS`, `APR_PRESS`, `VNV_PRESS`, `ALT_PRESS` | Validate the request, apply alternate-action behavior, and choose semantic mode ownership. |
| Capture events | `LATERAL_CAPTURED`, `GP_CAPTURED`, `GS_CAPTURED`, `VPTH_CAPTURED`, `ALTS_CAPTURE_STARTED`, `ALT_CAPTURED` | Move modes from armed to active and start annunciation timers. |
| Validity events | Nav source valid/invalid, GPS course active, VDEV valid, attitude valid/invalid | Reject unavailable selections or perform automatic reversion. |
| Reference events | Selected heading, selected altitude, VS reference, IAS/FLC reference | Update values without inventing mode transitions. |
| Protection events | `MAXSPEED_ENTER`, `MAXSPEED_EXIT`, `MINSPEED_ENTER`, `MINSPEED_EXIT` | Save and restore suspended modes separately from normal armed capture modes. |
| Profile/configuration events | HSI versus DG, Garmin PFD available, command bars supported, IAS versus FLC variant | Apply installation-dependent rules consistently. |

## Implementation Order

1. Fix the state representation before adding more transition logic:
   distinguish NAV from APR internally and replace the single armed-vertical
   field with a set or bitmask.
2. Implement FD/AP/default, HDG, ALT, VS, IAS/FLC, and `ALTS`.
3. Implement NAV semantic modes, arming, capture, deselection, and source-loss
   reversion.
4. Implement APR semantic modes with `GP` and `GS`.
5. Add VNAV and multiple simultaneous armed vertical modes.
6. Add protection suspend/restore behavior after normal mode transitions are
   stable.

## Open Questions And Required Tests

- Verify ordinary mode-key activation while FD is off against the first target
  MSFS aircraft. It is a high-confidence Garmin cross-check, not a complete GFC
  600 table.
- Verify whether selecting a different vertical mode while `VPTH` is active
  should always return `VPTH` to armed for the selected aircraft profile.
- Verify same-axis mode replacement and armed-mode preservation behavior in the
  chosen MSFS aircraft.
- Decide whether the first profile is GMC 605C-IAS or GMC 605C-FLC.
- Decide whether the first profile supports command bars, Garmin-PFD-style
  `ALTS`, HSI arming, and navigator autoswitching.
- Confirm which MSFS variables can reliably distinguish NAV from APR ownership,
  capture criteria, and protection entry/exit.
