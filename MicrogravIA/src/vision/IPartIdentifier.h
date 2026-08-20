#pragma once

#include "core/OperationResult.h"
#include "domain/PartIdentification.h"
#include "hardware/camera/CapturedImage.h"

class IPartIdentifier {
public:
    virtual ~IPartIdentifier() = default;
    virtual OperationResult<void> begin() = 0;
    virtual void shutdown() = 0;
    virtual bool isInitialized() const = 0;
    virtual OperationResult<void> healthCheck() const = 0;
    virtual OperationResult<void> selfTest() = 0;
    virtual OperationResult<PartIdentificationResult> identify(const CapturedImage& image) = 0;
};
