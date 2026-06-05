# GMC 605 Display And ESP32 Selection

## Goal

Keep the hardware choice simple for the restarted project.

The ESP32 is a display/input panel for MSFS. It does not run autopilot logic.

## Sources Used

- Existing project hardware/display decision document.
- User restart instruction.
- Espressif ESP32-S3-DevKitC-1 user guide: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html
- Espressif ESP-IDF LCD peripheral documentation: https://docs.espressif.com/projects/esp-idf/en/release-v5.2/esp32s3/api-reference/peripherals/lcd.html
- ESP Component Registry `nixy4/u8g2`: https://components.espressif.com/components/nixy4/u8g2/versions/0.1.4/readme?language=en
- U8g2 SSD1322 setup reference: https://github.com/olikraus/u8g2/wiki/u8g2setupcpp

## Decision

Use the existing SSD1322 SPI OLED for the first prototype.

Use an ESP32-S3 development board or module with PSRAM if available.

## Why This Fits The Restart

- The OLED only needs to show labels, references, and alerts.
- The SSD1322 256x64 format fits an annunciator-strip style display.
- The framebuffer is small.
- SPI is simple enough for ESP-IDF bring-up.
- ESP32-S3 has enough headroom for inputs, display, protocol, and diagnostics.
- Native USB is useful for the PC connector link.

## Display Content

The display should show:

- AP / FD / YD status.
- Active and armed lateral labels.
- Active and armed vertical labels.
- Selected heading, altitude, VS, and speed.
- Link, sim, and command fault messages.

It should not show complex maps, flight plans, synthetic vision, or real avionics pages.

## Monochrome Style Mapping

| Meaning | SSD1322 Treatment |
|---|---|
| Active mode | Bright steady text. |
| Armed mode | Dimmer or smaller steady text. |
| Alert | Slow flash or inverse video. |
| Failure | Fast inverse video. |
| Link/sim problem | Center message such as `LINK` or `SIM`. |

## ESP32 Recommendation

Development:

- Prefer `ESP32-S3-DevKitC-1-N8R8` or similar.
- 8 MB flash and 8 MB PSRAM gives comfortable headroom.
- Native USB helps with a direct PC connector link.

Final PCB:

- Prefer ESP32-S3 WROOM module with PSRAM.
- Avoid a no-PSRAM module until the display and diagnostics are stable.

## Interface Allocation

| Function | Interface |
|---|---|
| SSD1322 OLED | SPI master |
| Buttons | Direct GPIO or matrix scan |
| Encoders | PCNT where practical, otherwise GPIO ISR/debounce |
| PC connector | USB CDC first; UART or Wi-Fi later if needed |
| Debug | USB serial/JTAG and optional status LED |

## Driver Direction

Start with U8g2 for SSD1322 bring-up.

Likely setup families:

- `U8G2_SSD1322_NHD_256X64_*_4W_HW_SPI`
- `U8G2_SSD1322_ZJY_256X64_*_4W_HW_SPI`

The exact constructor depends on the module mapping and visible column offset.

Keep U8g2 behind a project renderer interface so it can be replaced later by a small native SSD1322 driver.

## Open Questions

- Exact SSD1322 module part number.
- Logic voltage and whether level shifting is needed.
- NHD or ZJY memory mapping.
- Required column offset.
- Final USB/UART/Wi-Fi link choice.
- Whether a future color display is worth the hardware change.

## Recommended Next Step

Do a focused display bring-up:

1. Draw a border.
2. Draw `AP`, `HDG`, `ALT`, `LINK`, and a reference number.
3. Test brightness, inverse video, and blink.
4. Verify readability through the real panel window.
