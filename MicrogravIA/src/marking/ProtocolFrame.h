#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

struct ProtocolFrame {
    static constexpr std::size_t Capacity = 128;
    std::array<std::uint8_t, Capacity> bytes{};
    std::size_t length{0};
};
