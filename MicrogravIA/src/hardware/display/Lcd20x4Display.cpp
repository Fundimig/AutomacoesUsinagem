#include "hardware/display/Lcd20x4Display.h"

#include <Arduino.h>
#include <Wire.h>

#include "config/BoardPins.h"
#include "config/FirmwareConfig.h"

namespace {
constexpr std::uint8_t ENABLE_MASK = 0x04;
constexpr std::uint8_t RS_MASK = 0x01;
constexpr std::uint8_t ROW_OFFSETS[4] = {0x00, 0x40, 0x14, 0x54};
}

OperationResult<void> Lcd20x4Display::begin() {
    if (initialized_) return OperationResult<void>::success();
    Wire.begin(BoardPins::I2C_SDA, BoardPins::I2C_SCL);
    Wire.setClock(100000);
    if (!probe()) {
        return OperationResult<void>::failure(SystemErrorCode::DisplayInitializationFailed, "LCD I2C backpack not found");
    }

    delay(50);
    writeNibble(0x30);
    delayMicroseconds(4500);
    writeNibble(0x30);
    delayMicroseconds(4500);
    writeNibble(0x30);
    delayMicroseconds(150);
    writeNibble(0x20);
    command(0x28);  // 4-bit, 2-line controller mode, 5x8 font.
    command(0x08);
    command(0x01);
    delayMicroseconds(2000);
    command(0x06);
    command(0x0C);
    initialized_ = true;
    return OperationResult<void>::success();
}

void Lcd20x4Display::shutdown() {
    if (initialized_) command(0x08);
    initialized_ = false;
}

OperationResult<void> Lcd20x4Display::reset() {
    shutdown();
    return begin();
}

OperationResult<void> Lcd20x4Display::healthCheck() const {
    if (!initialized_ || !probe()) {
        return OperationResult<void>::failure(SystemErrorCode::HardwareUnavailable, "LCD unavailable");
    }
    return OperationResult<void>::success();
}

OperationResult<void> Lcd20x4Display::selfTest() {
    auto health = healthCheck();
    if (!health) return health;
    show("MICROGRAV AUTO", "LCD OK", "", "");
    return OperationResult<void>::success();
}

void Lcd20x4Display::show(const char* line1, const char* line2, const char* line3, const char* line4) {
    if (!initialized_) return;
    writeLine(0, line1);
    writeLine(1, line2);
    writeLine(2, line3);
    writeLine(3, line4);
}

void Lcd20x4Display::command(std::uint8_t value) { send(value, false); }
void Lcd20x4Display::writeCharacter(std::uint8_t value) { send(value, true); }

void Lcd20x4Display::send(std::uint8_t value, bool dataMode) {
    const std::uint8_t mode = dataMode ? RS_MASK : 0;
    writeNibble((value & 0xF0) | mode);
    writeNibble(((value << 4) & 0xF0) | mode);
}

void Lcd20x4Display::writeNibble(std::uint8_t value) {
    Wire.beginTransmission(FirmwareConfig::LCD_ADDRESS);
    Wire.write(value | backlightMask_);
    Wire.endTransmission();
    pulseEnable(value);
}

void Lcd20x4Display::pulseEnable(std::uint8_t value) {
    Wire.beginTransmission(FirmwareConfig::LCD_ADDRESS);
    Wire.write(value | backlightMask_ | ENABLE_MASK);
    Wire.endTransmission();
    delayMicroseconds(1);
    Wire.beginTransmission(FirmwareConfig::LCD_ADDRESS);
    Wire.write((value | backlightMask_) & ~ENABLE_MASK);
    Wire.endTransmission();
    delayMicroseconds(50);
}

void Lcd20x4Display::writeLine(std::uint8_t row, const char* text) {
    command(0x80 | ROW_OFFSETS[row]);
    for (std::uint8_t column = 0; column < FirmwareConfig::LCD_COLUMNS; ++column) {
        const char character = (text != nullptr && text[column] != '\0') ? text[column] : ' ';
        writeCharacter(static_cast<std::uint8_t>(character));
        if (text == nullptr || text[column] == '\0') text = nullptr;
    }
}

bool Lcd20x4Display::probe() const {
    Wire.beginTransmission(FirmwareConfig::LCD_ADDRESS);
    return Wire.endTransmission() == 0;
}
