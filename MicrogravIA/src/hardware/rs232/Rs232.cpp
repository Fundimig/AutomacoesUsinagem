#include "hardware/rs232/Rs232.h"

#include "config/BoardPins.h"
#include "config/FirmwareConfig.h"

Rs232::Rs232() : serial_(1) {}

OperationResult<void> Rs232::begin() {
    if (initialized_) return OperationResult<void>::success();
    serial_.begin(
        FirmwareConfig::MICROGRAV_BAUD,
        SERIAL_8N1,
        BoardPins::RS232_RX,
        BoardPins::RS232_TX);
    if (!serial_.setPins(
            BoardPins::RS232_RX,
            BoardPins::RS232_TX,
            BoardPins::RS232_CTS,
            BoardPins::RS232_RTS) ||
        !serial_.setHwFlowCtrlMode(UART_HW_FLOWCTRL_CTS_RTS, 64)) {
        serial_.end();
        return OperationResult<void>::failure(SystemErrorCode::Rs232InitializationFailed, "UART RTS/CTS configuration failed");
    }
    initialized_ = true;
    return OperationResult<void>::success();
}

void Rs232::shutdown() {
    if (initialized_) serial_.end();
    initialized_ = false;
}

OperationResult<void> Rs232::reset() {
    shutdown();
    return begin();
}

OperationResult<void> Rs232::healthCheck() const {
    return initialized_ ? OperationResult<void>::success()
                        : OperationResult<void>::failure(SystemErrorCode::NotInitialized, "RS232 unavailable");
}

OperationResult<void> Rs232::selfTest() const { return healthCheck(); }

OperationResult<void> Rs232::write(const std::uint8_t* data, std::size_t size) {
    if (!initialized_) return OperationResult<void>::failure(SystemErrorCode::NotInitialized, "RS232 not initialized");
    if (data == nullptr || size == 0) return OperationResult<void>::failure(SystemErrorCode::InvalidArgument, "Empty RS232 frame");
    const std::size_t written = serial_.write(data, size);
    serial_.flush();
    if (written != size) return OperationResult<void>::failure(SystemErrorCode::Rs232WriteFailed, "Incomplete RS232 write", written);
    return OperationResult<void>::success();
}

int Rs232::available() { return initialized_ ? serial_.available() : 0; }
int Rs232::read() { return initialized_ ? serial_.read() : -1; }
