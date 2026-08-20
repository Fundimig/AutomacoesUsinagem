#include "hardware/buttons/StartButton.h"

#include "config/BoardPins.h"
#include "config/FirmwareConfig.h"

StartButton::StartButton()
    : button_(BoardPins::START_BUTTON, FirmwareConfig::BUTTON_DEBOUNCE_MS) {}

OperationResult<void> StartButton::begin() {
    button_.begin();
    return OperationResult<void>::success();
}

void StartButton::shutdown() { button_.shutdown(); }

OperationResult<void> StartButton::reset() {
    if (!isInitialized()) return OperationResult<void>::failure(SystemErrorCode::NotInitialized, "START not initialized");
    button_.reset();
    return OperationResult<void>::success();
}

bool StartButton::isInitialized() const { return button_.isInitialized(); }

OperationResult<void> StartButton::healthCheck() const {
    return isInitialized() ? OperationResult<void>::success()
                           : OperationResult<void>::failure(SystemErrorCode::NotInitialized, "START unavailable");
}

OperationResult<void> StartButton::selfTest() const { return healthCheck(); }
void StartButton::update() { button_.update(); }

bool StartButton::consume(StartButtonPressed& event) {
    return button_.consumePressed(event.timestampMs);
}
