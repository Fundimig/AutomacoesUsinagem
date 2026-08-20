#pragma once

#include "core/OperationResult.h"
#include "hardware/buttons/ButtonEvents.h"

class IStartButton {
public:
    virtual ~IStartButton() = default;
    virtual OperationResult<void> begin() = 0;
    virtual void shutdown() = 0;
    virtual OperationResult<void> reset() = 0;
    virtual bool isInitialized() const = 0;
    virtual OperationResult<void> healthCheck() const = 0;
    virtual OperationResult<void> selfTest() const = 0;
    virtual void update() = 0;
    virtual bool consume(StartButtonPressed& event) = 0;
};
