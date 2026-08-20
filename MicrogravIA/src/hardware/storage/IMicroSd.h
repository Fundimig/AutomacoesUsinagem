#pragma once

#include "core/OperationResult.h"

class IMicroSd {
public:
    virtual ~IMicroSd() = default;
    virtual OperationResult<void> begin() = 0;
    virtual void shutdown() = 0;
    virtual OperationResult<void> reset() = 0;
    virtual bool isInitialized() const = 0;
    virtual OperationResult<void> healthCheck() const = 0;
    virtual OperationResult<void> selfTest() const = 0;
};
