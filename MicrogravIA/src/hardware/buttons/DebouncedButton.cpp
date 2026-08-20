#include "hardware/buttons/DebouncedButton.h"

#include <Arduino.h>

DebouncedButton::DebouncedButton(gpio_num_t pin, std::uint32_t debounceMs)
    : pin_(pin), debounceMs_(debounceMs) {}

void DebouncedButton::begin() {
    pinMode(static_cast<std::uint8_t>(pin_), INPUT_PULLUP);
    initialized_ = true;
    reset();
}

void DebouncedButton::shutdown() {
    initialized_ = false;
    pressedPending_ = false;
}

void DebouncedButton::reset() {
    if (!initialized_) return;
    rawState_ = digitalRead(static_cast<std::uint8_t>(pin_));
    stableState_ = rawState_;
    lastRawChangeMs_ = millis();
    pressedPending_ = false;
}

void DebouncedButton::update() {
    if (!initialized_) return;
    const std::uint32_t now = millis();
    const int raw = digitalRead(static_cast<std::uint8_t>(pin_));
    if (raw != rawState_) {
        rawState_ = raw;
        lastRawChangeMs_ = now;
    }
    if (raw != stableState_ && static_cast<std::uint32_t>(now - lastRawChangeMs_) >= debounceMs_) {
        stableState_ = raw;
        if (stableState_ == LOW) {
            pressedTimestampMs_ = now;
            pressedPending_ = true;
        }
    }
}

bool DebouncedButton::consumePressed(std::uint32_t& timestampMs) {
    if (!pressedPending_) return false;
    pressedPending_ = false;
    timestampMs = pressedTimestampMs_;
    return true;
}
