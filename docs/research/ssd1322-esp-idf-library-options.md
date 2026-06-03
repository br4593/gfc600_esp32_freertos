# SSD1322 ESP-IDF Library Options

## Goal

Find practical SSD1322 display-library options for this ESP32-S3, ESP-IDF, GMC 605-style MSFS panel.

This is for simulator display hardware only.

## Sources Used

- ESP Component Registry `nixy4/u8g2`: https://components.espressif.com/components/nixy4/u8g2/versions/0.1.4/readme?language=en
- Upstream U8g2 SSD1322 setup reference: https://github.com/olikraus/u8g2/wiki/u8g2setupcpp
- ESP-IDF SPI master documentation: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/spi_master.html
- ESP-IDF LCD documentation: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/index.html
- ESP-IoT-Solution display documentation: https://espressif-docs.readthedocs-hosted.com/projects/espressif-esp-iot-solution/en/latest/display/screen.html
- ESPHome SSD1322 display component: https://esphome.io/components/display/ssd1322/
- Squeezelite-ESP32 project display support reference: https://github.com/sle118/squeezelite-esp32

## Confirmed Findings

### U8g2 Supports SSD1322

Upstream U8g2 lists SSD1322 constructors for several displays, including:

- `SSD1322 NHD_256X64`
- `SSD1322 ZJY_256X64`
- `SSD1322 NHD_128X64`
- `SSD1322 240X128`

For the likely 256x64 module, the relevant U8g2 setup family is:

- `U8G2_SSD1322_NHD_256X64_*_4W_HW_SPI`
- `U8G2_SSD1322_ZJY_256X64_*_4W_HW_SPI`

The `NHD` vs `ZJY` choice depends on the exact module memory mapping and visible offset.

### ESP-IDF U8g2 Component Exists

The ESP Component Registry has `nixy4/u8g2`, described as a U8g2 graphics component for ESP-IDF.

Important details from its registry page:

- It targets ESP-IDF 5.x.
- It provides ESP32 hardware I2C and SPI backends.
- It can be added with:

```text
idf.py add-dependency "nixy4/u8g2^0.1.4"
```

Risk:

- It is a third-party fork, not an Espressif-official display driver.
- It should be proven with the exact SSD1322 module before the firmware architecture depends on it.

### ESP-IDF SPI Driver Is Suitable

ESP-IDF's SPI master driver supports:

- SPI master operation.
- DMA-backed transfers.
- Multiple devices on one SPI bus.
- Thread-safe access if each SPI device is accessed by one task, or if shared-device access is protected.

This fits the project rule: one display task owns the SSD1322 SPI device.

### ESP-IDF `esp_lcd` Does Not Appear To Provide A Ready SSD1322 Driver

ESP-IDF has the modern `esp_lcd` framework, but I did not find a clean official `esp_lcd` SSD1322 panel component in the registry.

The ESP Component Registry has many `esp_lcd_*` panel drivers, but search results did not show an official SSD1322 component.

### ESP-IoT-Solution Mentions SSD1322

ESP-IoT-Solution display documentation lists SSD1322 as a supported gray display controller with max resolution `480 x 128`.

Risk:

- This is not the same as finding a current, clean, easy-to-add ESP-IDF 5.x component for SSD1322.
- It may be useful as reference material, but I would not make it the first integration path unless the exact component source is verified in a build.

### ESPHome Has SSD1322 SPI Support

ESPHome documents an `ssd1322_spi` display platform for 4-wire SPI and model `SSD1322 256x64`.

Risk:

- ESPHome is a full framework, not a direct drop-in ESP-IDF component.
- Its driver code may be useful as reference if we write a small native driver.

### Squeezelite-ESP32 Has SSD1322 Support

The Squeezelite-ESP32 project documents display support for SSD1322 over SPI.

Risk:

- It is an application-level project, not a small standalone driver.
- Its code may be useful as a reference, not as the clean first dependency.

## Options

| Option | Description | Pros | Cons | Recommendation |
|---|---|---|---|---|
| U8g2 via ESP-IDF component | Use `nixy4/u8g2` or port upstream U8g2 manually | Fastest route to text/fonts; SSD1322 support already exists | Third-party fork; may need constructor/offset tuning | Best first bring-up |
| Small custom SSD1322 driver | Implement init, framebuffer, text rendering hooks ourselves | Small, predictable, no heavy graphics stack | More work; need font rendering or bitmap fonts | Best long-term if U8g2 is awkward |
| ESP-IoT-Solution screen driver | Use/reuse Espressif solution-layer SSD1322 support | More official-ish than random code | Need verify current component/build compatibility | Investigate only if U8g2 fails |
| ESPHome driver extraction | Study ESPHome SSD1322 driver | Known 256x64 SPI behavior | Not a direct ESP-IDF component | Reference only |
| Squeezelite-ESP32 extraction | Study its display driver | Proven in ESP32 app | App-specific integration | Reference only |

## Recommended Path

### Phase 1: Bring-Up

Use U8g2 through the ESP-IDF component path if it builds cleanly.

Target:

- ESP32-S3
- SPI 4-wire
- SSD1322 256x64
- hardware SPI
- full framebuffer mode if RAM allows

Try both likely SSD1322 mappings if needed:

- `NHD_256X64`
- `ZJY_256X64`

### Phase 2: Project Wrapper

Do not expose U8g2 directly to the rest of the firmware.

Create a project display abstraction:

```text
display_renderer
    init()
    clear()
    draw_label(slot, text, style)
    draw_reference(slot, value, style)
    present()
```

Then the project can later replace U8g2 with a custom driver or color TFT driver.

### Phase 3: Long-Term Driver Choice

If U8g2 is stable:

- keep it
- freeze known-good version in the dependency lock
- only use the subset we need

If U8g2 causes integration problems:

- write a small SSD1322-only driver
- keep the same `display_renderer` API
- reuse the already defined display model and slots

## Open Questions

- Exact OLED module: Newhaven-compatible, ZJY-compatible, or other SSD1322 mapping?
- Is the module breakout already level-shifted for 3.3 V logic?
- Does it need a special column offset to center the visible 256 pixels?
- Does the SSD1322 board expose 4-wire SPI cleanly, or is it strapped for parallel mode?

## Recommended Next Step

Create a tiny ESP-IDF display bring-up project before writing the real application:

1. Add the U8g2 ESP-IDF component.
2. Initialize SSD1322 over hardware SPI.
3. Draw a border, `AP`, `HDG`, `ALT`, and a grayscale ramp.
4. Verify orientation, offsets, contrast, and update speed.
5. Only then lock the display dependency choice.

