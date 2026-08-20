#pragma once

#include <cstddef>
#include <cstdint>

#include "core/OperationResult.h"

class IRS232 {
public:
    virtual ~IRS232() = default;
    virtual OperationResult<void> begin() = 0;
    virtual void shutdown() = 0;
    virtual OperationResult<void> reset() = 0;
    virtual bool isInitialized() const = 0;
    virtual OperationResult<void> healthCheck() const = 0;
    virtual OperationResult<void> selfTest() const = 0;
    virtual OperationResult<void> write(const std::uint8_t* data, std::size_t size) = 0;
    virtual int available() = 0;
    virtual int read() = 0;
};
