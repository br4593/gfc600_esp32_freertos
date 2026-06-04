# GMC 605 Display And ESP32 Selection

## Goal

Pick a practical display and ESP32 board/module for a GMC 605-style MSFS autopilot panel.

Known project constraints:

- Panel target: Garmin GMC 605-style control panel.
- Existing display in hand: SSD1322 OLED over SPI.
- Firmware platform: ESP-IDF + FreeRTOS, not Arduino.
- Simulator only: no real aircraft use.

Implementation ownership is defined in
[GMC 605 Firmware Architecture](gmc605-firmware-architecture.md).

## Sources Used

- Garmin `GFC 600 Automatic Flight Control System (with Color Display) Pilot's Guide`, `190-03090-00 Rev. A`: https://static.garmin.com/pumac/190-03090-00_a.pdf
- Espressif ESP32-S3-DevKitC-1 user guide: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html
- Espressif ESP-IDF LCD peripheral documentation: https://docs.espressif.com/projects/esp-idf/en/release-v5.2/esp32s3/api-reference/peripherals/lcd.html
- Espressif ESP-IDF SPI master documentation: https://docs.espressif.com/projects/esp-idf/en/v3.3.4/api-reference/peripherals/spi_master.html
- ESP Component Registry `nixy4/u8g2`: https://components.espressif.com/components/nixy4/u8g2/versions/0.1.4/readme?language=en
- Upstream U8g2 SSD1322 setup reference: https://github.com/olikraus/u8g2/wiki/u8g2setupcpp
- BuyDisplay / EastRising 2.7 inch SSD1322 OLED product page: https://www.buydisplay.com/white-grayscale-2-7-inch-oled-256x64-display-panel-ssd1322
- Orient Display 3.12 inch SSD1322 OLED product page: https://orientdisplay.com/products/3-12-oled-256x64-monochrome-parallel-spi-interface/
- Adafruit 1.9 inch 320x170 ST7789 IPS TFT: https://www.adafruit.com/product/5394
- Waveshare 2 inch 320x240 ST7789 IPS TFT wiki: https://www.waveshare.com/wiki/2inch_LCD_Module

## Display Requirements

For a GMC 605-style display, the useful information is mostly short labels:

- lateral active/armed modes
- AP/YD state
- alerts/messages
- vertical active/armed modes
- selected references

The display needs good contrast, stable refresh, and readable annunciation. It does not need photo or map rendering.

## Candidate Displays

| Display | Resolution | Color | Interface | Fit For GMC 605 | Notes |
|---|---:|---|---|---|---|
| Existing SSD1322 OLED | 256x64 | monochrome / grayscale | SPI | Very good shape fit | Best first prototype. Wide 4:1 format fits an annunciator strip. No true Garmin active/armed colors. |
| 3.12 inch SSD1322 OLED | 256x64 | monochrome / grayscale | SPI or parallel | Very good shape fit | Same logic as existing display, larger physical size depending module. |
| 1.9 inch ST7789 IPS TFT | 320x170 | 16-bit color | SPI | Good but taller than needed | Color supports Garmin-style green/white/yellow/red. Aspect ratio is not as strip-like. |
| 2.0 inch ST7789 IPS TFT | 320x240 | 16-bit color | SPI | Usable, not ideal shape | More pixels, common driver, but display is too tall for a realistic GMC 605 strip. |
| 2.9 inch 320x120 bar TFT | 320x120 | color | SPI/MCU/RGB varies | Potentially best visual match | Good aspect ratio and color, but sourcing and driver integration are less standardized. |

## Framebuffer Cost

Approximate raw framebuffer sizes:

| Display | Format | Bytes |
|---|---:|---:|
| SSD1322 256x64 | 4-bit grayscale | 8 KB |
| SSD1322 256x64 | 1-bit monochrome shadow buffer | 2 KB |
| ST7789 320x170 | RGB565 | 106 KB |
| ST7789 320x240 | RGB565 | 150 KB |

Practical result:

- SSD1322 is easy on RAM and SPI bandwidth.
- Color TFT is still reasonable on ESP32-S3, but PSRAM is useful if using LVGL, double buffering, or more complex UI composition.

## Recommendation

### Decision

Use the existing SSD1322 SPI OLED for the first functional prototype.

### Why

- It is already available.
- The 256x64 wide format matches a GMC annunciator-strip style better than common square/tall TFTs.
- The display memory and SPI bandwidth are small.
- Text labels are the primary content, so color is useful but not mandatory.
- Monochrome/grayscale annunciation can mimic Garmin color priority using brightness, inverse video, blinking, and slot position.

### When To Replace It

Move to a color TFT only if one of these becomes important:

- You want closer visual mimicry of Garmin green active / white armed / yellow alert / red fail.
- You want a richer GMC 605 color display mockup with icons or soft status graphics.
- You find a reliable 320x120 or similar bar TFT module with a clean ESP-IDF driver path.

## Monochrome Display Fit

The SSD1322 cannot reproduce Garmin colors, but the wide format can still show
the required active, armed, status, message, and reference slots. The renderer
style mapping and layout are owned by
[GMC 605 Firmware Architecture](gmc605-firmware-architecture.md).

## ESP32 Board Recommendation

### Development Board

Use `ESP32-S3-DevKitC-1-N8R8` for development if available.

Why this board fits:

- ESP32-S3 class gives dual-core MCU performance suitable for display, inputs, USB/serial/Wi-Fi bridge, and state management.
- The `N8R8` variant gives 8 MB flash and 8 MB PSRAM, useful headroom for display buffers and diagnostics.
- Native USB support is useful for development and for a future USB serial bridge.
- Most GPIOs are broken out, useful while the PCB/pinout is still changing.

### Final PCB Module

Prefer an ESP32-S3 WROOM module with PSRAM, for example:

- `ESP32-S3-WROOM-1-N8R8`
- `ESP32-S3-WROOM-1-N16R8` if you want more flash headroom

Avoid choosing a no-PSRAM module unless the design is locked to the SSD1322 and a small static UI.

## Interface Allocation

Recommended high-level allocation:

| Function | ESP32 Peripheral / Task |
|---|---|
| SSD1322 OLED | SPI master, display task owns device |
| Button matrix / discrete inputs | GPIO interrupts or periodic scan task |
| Rotary encoders | PCNT peripheral if enough channels, otherwise GPIO ISR + debounce |
| MSFS bridge | USB CDC serial, Wi-Fi TCP/UDP, or UART to host bridge |
| Mode state | FreeRTOS state manager task |
| Logging/diagnostics | USB serial and optional Wi-Fi debug endpoint |

## Implementation Notes

- Keep the display driver behind a small interface: `draw_label(slot, text, style)`.
- Do not let mode logic depend on SSD1322 details.
- Start with SPI-only SSD1322 using an 8 KB framebuffer or dirty-region rendering.
- If changing to ST7789 later, preserve the same display model and replace only the renderer.
- Use a single display task to own SPI transactions for the OLED.
- If other SPI devices are added later, use the ESP-IDF SPI bus/device model and avoid concurrent access to the same device from multiple tasks.

## SSD1322 Driver Decision

Use U8g2 through an ESP-IDF component for the first display bring-up, but keep
it behind the project `display_renderer` interface.

Confirmed useful U8g2 setup families for a 256x64 SSD1322 module:

- `U8G2_SSD1322_NHD_256X64_*_4W_HW_SPI`
- `U8G2_SSD1322_ZJY_256X64_*_4W_HW_SPI`

The `NHD` versus `ZJY` choice depends on the module memory mapping and visible
column offset. The third-party `nixy4/u8g2` ESP-IDF component is the fastest
bring-up path, but it must be tested with the exact OLED before it becomes a
locked dependency.

| Option | Use | Decision |
|---|---|---|
| U8g2 ESP-IDF component | Fast text, font, and SSD1322 bring-up | First choice |
| Small native SSD1322 driver | Predictable long-term driver with an 8 KB framebuffer | Fallback if U8g2 is awkward |
| ESP-IoT-Solution, ESPHome, or application driver extraction | Reference implementations | Do not use as the first dependency |

If U8g2 is stable, freeze a known-good version and use only the required
subset. If it is not stable, replace it with a small SSD1322-only driver while
keeping the same renderer API.

## Open Questions

- Exact SSD1322 module part number and logic voltage.
- Whether the module uses Newhaven-compatible or ZJY-compatible memory mapping.
- Whether a column offset is required to center the visible 256 pixels.
- Whether the display board exposes 4-wire SPI cleanly or is strapped for a
  parallel interface.
- Physical active area needed to match your custom PCB window.
- Whether your final panel needs Garmin-style color strongly enough to justify a color TFT.
- Whether the MSFS bridge will be USB CDC, Wi-Fi, or a separate host-side SimConnect app over UART.

## Recommended Next Step

Prototype the SSD1322 with ESP-IDF first:

1. Add the U8g2 ESP-IDF component in a small bring-up target.
2. Try the `NHD_256X64` and `ZJY_256X64` hardware-SPI mappings.
3. Draw a border, `AP`, `HDG`, `ALT`, and a grayscale ramp.
4. Verify orientation, offsets, contrast, update speed, and readability through
   the real panel window.
5. Only then lock the display dependency or decide if color is worth changing
   hardware.

