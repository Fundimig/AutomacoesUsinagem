#pragma once

#include <array>
#include <cstdint>

#include "domain/PartIdentification.h"

enum class MarkingMode : std::uint8_t {
    Linear,
    Circular,
    Plot,
    DataMatrix2D
};

struct MarkingProgram {
    PartId partId{PartId::Unknown};
    MarkingMode mode{MarkingMode::Linear};
    std::uint8_t block{0};
    std::uint8_t font{0};
    std::uint16_t xTenthsMm{0};
    std::uint16_t yTenthsMm{0};
    std::uint16_t angle{0};
    std::uint16_t spacingTenthsMm{0};
    std::uint16_t heightTenthsMm{0};
    std::array<char, 64> markingData{};
    bool configured{false};
    bool validatedForProduction{false};
};
