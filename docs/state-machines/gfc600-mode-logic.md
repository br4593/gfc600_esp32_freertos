# GFC 600-Style Display Annunciation Model

## Goal

Define what the ESP32 may display for the GMC 605-style panel.

This is not an autopilot state machine. MSFS owns the actual autopilot logic. The
Python connector observes MSFS, derives a display snapshot, and sends that
snapshot to the ESP32.

Simulator boundary: this project is for Microsoft Flight Simulator only.

## Sources Used

- User restart instruction: MSFS handles AP logic; ESP32 displays MSFS state and sends button commands.
- Garmin `GFC 600 Pilot's Guide`, `190-01488-00 Rev. H`: https://static.garmin.com/pumac/190-01488-00_h.pdf
- ManualsLib mirror of the GMC 605 system indications page: https://www.manualslib.com/manual/1853204/Garmin-Gfc-600.html?page=19
- [MSFS SimVar And Event Map](../research/msfs-gmc605-simvar-event-map.md)
- [Firmware Architecture](../design-decisions/gmc605-firmware-architecture.md)

## Confirmed Facts

- The GMC 605 LCD has named regions for active lateral mode, armed lateral mode,
  active vertical mode, armed vertical modes, mode reference, and status
  messages/alerts.
- Active mode annunciations use a larger upper display area. Armed mode
  annunciations use a smaller lower display area.
- Text may flash between normal and inverse video when pilot attention is needed.
- The message area can show up to four short messages.
- AP, FD, and YD state is indicated by LEDs adjacent to the AP, FD, and YD keys.
  These are not normal center LCD mode labels.
- Manual AP disengagement flashes the AP LED yellow for five seconds.
- Yaw damper engagement illuminates the YD LED green; disengagement can flash the
  YD LED yellow for five seconds.
- The GMC 605 annunciates `ALT`, `VS`, and `IAS`; their references are displayed
  in the mode reference area when the installation provides them.
- `ALTS` is an armed vertical mode in installations that support selected
  altitude capture. During capture, `ALTS` flashes for up to 10 seconds and `ALT`
  appears.
- `GP` is glidepath mode and relies on a GPS glidepath source. `GS` is
  glideslope mode and relies on a localizer/glideslope source.
- `LVL` and `GA` can appear in both lateral and vertical mode fields.

## Project Rules

- The ESP32 renders connector snapshots.
- The ESP32 does not decide active, armed, captured, reverted, or protected AP
  modes.
- Button presses are command requests only.
- A command result is not proof that a mode changed. The next MSFS-derived
  snapshot is the authority.
- Aircraft-specific behavior belongs in the Python connector adapter.

## Display Snapshot Fields

Minimum useful fields:

| Field | Example |
|---|---|
| `ap` | `on`, `off`, `disconnect_alert`, `fail` |
| `fd` | `on`, `off`, `fail` |
| `yd` | `on`, `off`, `not_installed`, `fail` |
| `lat_active` | `ROL`, `HDG`, `GPS`, `VOR`, `LOC`, `VAPP`, `BC`, `LVL`, `GA` |
| `lat_armed` | `GPS`, `VOR`, `LOC`, `VAPP`, `BC`, or `NONE` |
| `vert_active` | `PIT`, `ALT`, `VS`, `IAS`, `FLC`, `GS`, `GP`, `LVL`, `GA` |
| `vert_armed` | list such as `ALTS`, `GS`, `GP`, `VPTH` |
| `selected_heading` | `123` degrees |
| `selected_altitude` | `5500` ft |
| `selected_vs` | `+500` fpm |
| `selected_speed` | `120` kt |
| `messages` | `LINK`, `SIM`, `PFT`, `DISABLD KEY`, `CMD FAIL` |

The exact JSON names can evolve, but the meaning should stay stable.

## LCD Slots

GMC 605-style logical layout:

```text
+------------------------------------------------------------+
| Active lateral | Active vertical | Mode reference | Message |
| Armed lateral  | Armed vertical  | Mode reference | area    |
+------------------------------------------------------------+
```

Project rendering rules:

| Slot | Content |
|---|---|
| Left top | Active lateral label, large. Blank if unknown or not active. |
| Left bottom | Armed lateral label, smaller. Blank if no armed lateral mode. |
| Center top | Active vertical label, large. Blank if unknown or not active. |
| Center bottom | Armed vertical labels, smaller. Blank if no armed vertical mode. |
| Center/right reference | Selected vertical reference when applicable. |
| Right message area | Up to four short status messages or alerts. |
| AP/FD/YD LEDs | Key-adjacent LED state, not LCD text. |

## Lateral Mode Labels

Use the real GMC 605 text in the snapshot, not debug-only suffix labels.

| Source / Mode | LCD Text |
|---|---|
| GPS navigation | `GPS` |
| GPS approach | `GPS` plus `GP` armed or active when glidepath is available |
| VOR navigation | `VOR` |
| VOR approach | `VAPP` on the GMC 605 |
| Localizer navigation | `LOC` |
| Localizer approach | `LOC` plus `GS` armed or active when glideslope is available |
| Backcourse | `BC` |
| Heading | `HDG` |
| Roll hold | `ROL` |
| Level / go-around | `LVL`, `GA` |
| None / unknown | blank on the realistic panel |

The connector may keep richer diagnostic fields later, but the display snapshot
sent to the ESP32 should use the actual panel annunciation text.

## Reference Display

Only show references that belong to the active mode or are useful for the current
snapshot.

| Active Mode | Reference Text |
|---|---|
| `ALT` | selected or captured altitude, if known |
| `VS` | vertical speed reference |
| `IAS` | airspeed reference |
| `FLC` | airspeed reference, only for profiles using FLC |
| `PIT` | pitch reference, if the aircraft exposes it |
| Other modes | blank unless an aircraft adapter provides a confirmed reference |

The ESP32 can format numbers, but it must not decide which reference is relevant
to the current mode.

## Style Mapping For Monochrome OLED

The SSD1322 cannot reproduce Garmin colors. Use style metadata from the connector
or simple local rendering rules.

| Meaning | OLED Substitute |
|---|---|
| Active mode | Bright steady upper text. |
| Armed mode | Smaller lower text. |
| New capture/attention | Slow flash or inverse flash with expiry. |
| Manual AP/YD disconnect | Key LED equivalent flashes for about five seconds. |
| Failure | Fast inverse flash and message area text. |
| Unavailable | Blank slot or `DISABLD KEY` / `SIM` / `LINK` message. |

## What The ESP32 Must Not Do

Do not implement these in firmware:

- NAV/APR semantic conversion.
- GP/GS arming.
- ALTS capture.
- VNAV path logic.
- Overspeed or underspeed protection transitions.
- Garmin-style automatic reversion rules.
- Aircraft-specific LVar/HVar/Input Event behavior.

Those belong in the connector or aircraft adapter, not in ESP32 display firmware.

## Connector Responsibility

The connector can be simple first:

1. Read generic MSFS AP SimVars.
2. Map obvious states to real GMC 605-style display labels.
3. Leave uncertain fields blank or mark them as debug-only rather than inventing
   a Garmin transition.
4. Send a full snapshot to ESP32.
5. Send SimConnect events when ESP32 commands arrive.
6. Read back state and send the next snapshot.

If generic SimVars are not enough, create an aircraft adapter on the PC side.

## Open Questions

- First target aircraft for mapping and testing.
- Whether the first speed mode label should be `IAS` or `FLC`.
- Which vertical labels are reliable from generic SimVars in that aircraft.
- Whether the connector should hide unknown labels or show a debug-only marker.
- Exact capture flash timing and inverse-video behavior for each target aircraft
  profile.

## Recommended Next Step

Pick one first aircraft profile and limit the first real MSFS label set to AP,
FD, YD, HDG, GPS/VOR/LOC, BC, ALT, VS, IAS/FLC, ALTS, GS/GP if available, and
selected references.
