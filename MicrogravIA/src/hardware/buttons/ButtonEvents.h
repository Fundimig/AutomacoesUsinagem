#pragma once

#include <cstdint>

struct StartButtonPressed {
    std::uint32_t timestampMs{0};
};

struct ResetButtonPressed {
    std::uint32_t timestampMs{0};
};
