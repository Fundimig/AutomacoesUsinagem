#pragma once

#include <HardwareSerial.h>

#include "hardware/rs232/IRS232.h"

class Rs232 final : public IRS232 {
public:
    Rs232();
    OperationResult<void> begin() override;
    void shutdown() override;
    OperationResult<void> reset() override;
    bool isInitialized() const override { return initialized_; }
    OperationResult<void> healthCheck() const override;
    OperationResult<void> selfTest() const override;
    OperationResult<void> write(const std::uint8_t* data, std::size_t size) override;
    int available() override;
    int read() override;

private:
    HardwareSerial serial_;
    bool initialized_{false};
};
