#pragma once

#include <cstdint>

enum class PartId : std::uint8_t {
    Unknown = 0,
    Part031,
    Part045
};

struct PartIdentificationResult {
    PartId partId{PartId::Unknown};
    float confidence{0.0F};
    std::uint32_t x{0};
    std::uint32_t y{0};
    std::uint32_t width{0};
    std::uint32_t height{0};
};

inline const char* partIdToString(PartId partId) {
    switch (partId) {
        case PartId::Part031: return "031";
        case PartId::Part045: return "045";
        default: return "UNKNOWN";
    }
}
