#include "hardware/buttons/ResetButton.h"

#include "config/BoardPins.h"
#include "config/FirmwareConfig.h"

ResetButton::ResetButton()
    : button_(BoardPins::RESET_BUTTON, FirmwareConfig::BUTTON_DEBOUNCE_MS) {}

OperationResult<void> ResetButton::begin() {
    button_.begin();
    return OperationResult<void>::success();
}

void ResetButton::shutdown() { button_.shutdown(); }

OperationResult<void> ResetButton::reset() {
    if (!isInitialized()) return OperationResult<void>::failure(SystemErrorCode::NotInitialized, "RESET not initialized");
    button_.reset();
    return OperationResult<void>::success();
}

bool ResetButton::isInitialized() const { return button_.isInitialized(); }

OperationResult<void> ResetButton::healthCheck() const {
    return isInitialized() ? OperationResult<void>::success()
                           : OperationResult<void>::failure(SystemErrorCode::NotInitialized, "RESET unavailable");
}

OperationResult<void> ResetButton::selfTest() const { return healthCheck(); }
void ResetButton::update() { button_.update(); }

bool ResetButton::consume(ResetButtonPressed& event) {
    return button_.consumePressed(event.timestampMs);
}
