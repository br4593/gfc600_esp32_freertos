# Project Documentation

This project is an MSFS-only GMC 605 / GFC 600-style simulator panel. The
documents are intentionally split by ownership so the same behavior is not
described in several places.

## Core Documents

| Document | Owns |
|---|---|
| [GFC 600 Mode Logic](state-machines/gfc600-mode-logic.md) | Mode states, button behavior, active/armed transitions, capture, deselection, reversion, and protection logic |
| [GFC 600 Mode Logic Test Plan](test-plans/gfc600-mode-logic-test-plan.md) | Expected test scenarios and pass criteria |
| [MSFS SimVar And Event Map](research/msfs-gmc605-simvar-event-map.md) | Simulator variables, events, confidence, and aircraft-adapter concerns |
| [GMC 605 Firmware Architecture](design-decisions/gmc605-firmware-architecture.md) | ESP-IDF tasks, modules, data flow, display model, host protocol, and bring-up order |
| [GMC 605 Display And ESP32 Selection](design-decisions/gmc605-display-and-esp32-selection.md) | ESP32, display, SSD1322 driver, and hardware decisions |

## Editing Rules

- Add mode behavior only to the mode-logic document.
- Add a test when a mode rule is added or changed.
- Add MSFS-specific mapping only to the SimVar/event map.
- Add task, module, protocol, or renderer decisions only to firmware
  architecture.
- Add hardware or display-driver decisions only to the hardware selection
  document.
- Do not create a new document for one mode, one button, or one workflow unless
  it cannot fit one of the owners above.
