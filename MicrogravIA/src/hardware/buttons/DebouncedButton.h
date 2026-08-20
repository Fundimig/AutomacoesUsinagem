#pragma once

#include <cstdint>

#include <driver/gpio.h>

class DebouncedButton {
public:
    DebouncedButton(gpio_num_t pin, std::uint32_t debounceMs);

    void begin();
    void shutdown();
    void reset();
    void update();
    bool consumePressed(std::uint32_t& timestampMs);
    bool isInitialized() const { return initialized_; }

private:
    gpio_num_t pin_;
    std::uint32_t debounceMs_;
    bool initialized_{false};
    int rawState_{1};
    int stableState_{1};
    std::uint32_t lastRawChangeMs_{0};
    std::uint32_t pressedTimestampMs_{0};
    bool pressedPending_{false};
};
