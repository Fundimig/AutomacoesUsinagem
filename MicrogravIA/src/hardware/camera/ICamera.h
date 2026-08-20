#pragma once

#include "core/OperationResult.h"
#include "hardware/camera/CapturedImage.h"

class ICamera {
public:
    virtual ~ICamera() = default;
    virtual OperationResult<void> begin() = 0;
    virtual void shutdown() = 0;
    virtual OperationResult<void> reset() = 0;
    virtual bool isInitialized() const = 0;
    virtual OperationResult<void> healthCheck() const = 0;
    virtual OperationResult<void> selfTest() = 0;
    virtual OperationResult<CapturedImage> capture() = 0;
    virtual void release(CapturedImage& image) = 0;
};
