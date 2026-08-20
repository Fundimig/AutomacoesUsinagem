#pragma once

#include <cstddef>
#include <cstdint>

#include "vision/IPartIdentifier.h"

class EdgeImpulsePartIdentifier final : public IPartIdentifier {
public:
    OperationResult<void> begin() override;
    void shutdown() override;
    bool isInitialized() const override { return initialized_; }
    OperationResult<void> healthCheck() const override;
    OperationResult<void> selfTest() override;
    OperationResult<PartIdentificationResult> identify(const CapturedImage& image) override;

private:
    static int getSignalData(std::size_t offset, std::size_t length, float* output);
    OperationResult<PartIdentificationResult> runModel();

    static const std::uint8_t* activeModelRgb_;
    std::uint8_t* sourceRgb_{nullptr};
    std::uint8_t* modelRgb_{nullptr};
    bool initialized_{false};
};
