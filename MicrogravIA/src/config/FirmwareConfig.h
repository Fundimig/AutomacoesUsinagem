#pragma once

#include <cstdint>

namespace FirmwareConfig {

constexpr std::uint32_t SERIAL_BAUD = 115200;
constexpr std::uint32_t BUTTON_DEBOUNCE_MS = 50;
constexpr std::uint32_t COMPLETED_DISPLAY_MS = 3000;
constexpr float MINIMUM_VISION_CONFIDENCE = 0.50F;

constexpr std::uint8_t LCD_ADDRESS = 0x27;
constexpr std::uint8_t LCD_COLUMNS = 20;
constexpr std::uint8_t LCD_ROWS = 4;

constexpr std::uint32_t MICROGRAV_BAUD = 57600;

}  // namespace FirmwareConfig
