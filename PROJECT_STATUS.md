# Project Status

## Current State

- The ESP-IDF firmware skeleton contains the `gmc605_core` component and initial AP/FD mode handling.
- The current firmware state model has one active lateral mode, one armed lateral mode, one active vertical mode, and one armed vertical mode.
- The current firmware state model is not yet sufficient for the full GFC 600 transition logic.

## Latest Change

- Consolidated overlapping documentation into the core set listed in
  `docs/README.md`.
- `docs/state-machines/gfc600-mode-logic.md` is now the single authoritative
  source for states and mode transitions.
- Merged display workflow and hardware-to-MSFS workflow content into firmware
  architecture.
- Merged SSD1322 library research into the display and ESP32 hardware decision.
- No firmware code was changed during this documentation pass.

## Required Model Changes Before Full Transition Logic

- Distinguish Navigation mode from Approach mode internally even when both render as `GPS` or `LOC`.
- Replace the single armed-vertical field with a set or bitmask. The GFC 600 can show multiple armed vertical modes simultaneously.
- Store protection restore targets separately from normal capture-armed modes.

## Validation

- Checked the remaining documents for links to superseded files.
- Checked Markdown links between the core documents.
- Firmware build was not run because this pass changed documentation only.
