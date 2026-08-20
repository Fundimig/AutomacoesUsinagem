#pragma once

#include <cstdint>

#include "core/OperationResult.h"
#include "domain/MarkingProgram.h"

enum class MarkingEvent : std::uint8_t {
    None,
    MarkingFinished,
    CountFinished,
    OutOfArea,
    HardwareFault,
    UnknownResponse
};

class IMarker {
public:
    virtual ~IMarker() = default;
    virtual OperationResult<void> selfTest() const = 0;
    virtual OperationResult<void> start(const MarkingProgram& program) = 0;
    virtual OperationResult<void> stop() = 0;
    virtual MarkingEvent poll() = 0;
};
