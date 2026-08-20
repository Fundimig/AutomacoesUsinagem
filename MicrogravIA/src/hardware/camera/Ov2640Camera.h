#pragma once

#include "hardware/camera/ICamera.h"

class Ov2640Camera final : public ICamera {
public:
    OperationResult<void> begin() override;
    void shutdown() override;
    OperationResult<void> reset() override;
    bool isInitialized() const override { return initialized_; }
    OperationResult<void> healthCheck() const override;
    OperationResult<void> selfTest() override;
    OperationResult<CapturedImage> capture() override;
    void release(CapturedImage& image) override;

private:
    bool initialized_{false};
};
