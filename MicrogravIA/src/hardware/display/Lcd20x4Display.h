#pragma once

#include <cstdint>

#include "hardware/display/IDisplay.h"

class Lcd20x4Display final : public IDisplay {
public:
    OperationResult<void> begin() override;
    void shutdown() override;
    OperationResult<void> reset() override;
    bool isInitialized() const override { return initialized_; }
    OperationResult<void> healthCheck() const override;
    OperationResult<void> selfTest() override;
    void show(const char* line1, const char* line2, const char* line3, const char* line4) override;

private:
    void command(std::uint8_t value);
    void writeCharacter(std::uint8_t value);
    void send(std::uint8_t value, bool dataMode);
    void writeNibble(std::uint8_t value);
    void pulseEnable(std::uint8_t value);
    void writeLine(std::uint8_t row, const char* text);
    bool probe() const;

    bool initialized_{false};
    std::uint8_t backlightMask_{0x08};
};
