#include "hardware/HardwareManager.h"

#include <Arduino.h>

HardwareManager::HardwareManager(
    ICamera& camera,
    IStartButton& startButton,
    IResetButton& resetButton,
    IDisplay& display,
    IMicroSd& microSd,
    IRS232& rs232)
    : camera_(camera),
      startButton_(startButton),
      resetButton_(resetButton),
      display_(display),
      microSd_(microSd),
      rs232_(rs232) {}

OperationResult<void> HardwareManager::begin() {
    auto result = display_.begin();
    if (!result) return result;
    result = startButton_.begin();
    if (!result) return result;
    result = resetButton_.begin();
    if (!result) return result;
    result = camera_.begin();
    if (!result) return result;
    result = rs232_.begin();
    if (!result) return result;

    const auto storage = microSd_.begin();
    storageAvailable_ = storage.isSuccess();
    if (!storageAvailable_) {
        Serial.println("[HW] microSD unavailable (optional in V0.1)");
    }
    return OperationResult<void>::success();
}

void HardwareManager::shutdown() {
    rs232_.shutdown();
    microSd_.shutdown();
    camera_.shutdown();
    resetButton_.shutdown();
    startButton_.shutdown();
    display_.shutdown();
    storageAvailable_ = false;
}

OperationResult<void> HardwareManager::healthCheck() const {
    auto result = display_.healthCheck();
    if (!result) return result;
    result = startButton_.healthCheck();
    if (!result) return result;
    result = resetButton_.healthCheck();
    if (!result) return result;
    result = camera_.healthCheck();
    if (!result) return result;
    return rs232_.healthCheck();
}

OperationResult<void> HardwareManager::selfTest() {
    auto result = display_.selfTest();
    if (!result) return result;
    result = startButton_.selfTest();
    if (!result) return result;
    result = resetButton_.selfTest();
    if (!result) return result;
    result = camera_.selfTest();
    if (!result) return result;
    result = rs232_.selfTest();
    if (!result) return result;
    if (storageAvailable_ && !microSd_.selfTest()) {
        storageAvailable_ = false;
        Serial.println("[HW] microSD failed self-test (optional in V0.1)");
    }
    return OperationResult<void>::success();
}

void HardwareManager::update() {
    startButton_.update();
    resetButton_.update();
}
