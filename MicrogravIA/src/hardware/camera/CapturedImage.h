#pragma once

#include <cstddef>
#include <cstdint>

enum class CapturedImageFormat : std::uint8_t {
    Jpeg
};

struct CapturedImage {
    const std::uint8_t* data{nullptr};
    std::size_t size{0};
    std::uint16_t width{0};
    std::uint16_t height{0};
    CapturedImageFormat format{CapturedImageFormat::Jpeg};
    void* ownerHandle{nullptr};
};
