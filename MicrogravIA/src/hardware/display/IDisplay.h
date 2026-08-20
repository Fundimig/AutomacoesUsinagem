#pragma once

#include "core/OperationResult.h"

class IDisplay {
public:
    virtual ~IDisplay() = default;
    virtual OperationResult<void> begin() = 0;
    virtual void shutdown() = 0;
    virtual OperationResult<void> reset() = 0;
    virtual bool isInitialized() const = 0;
    virtual OperationResult<void> healthCheck() const = 0;
    virtual OperationResult<void> selfTest() = 0;
    virtual void show(const char* line1, const char* line2 = "", const char* line3 = "", const char* line4 = "") = 0;
};
