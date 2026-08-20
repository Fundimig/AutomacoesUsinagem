#pragma once

#include "hardware/storage/IMicroSd.h"

class MicroSd final : public IMicroSd {
public:
    OperationResult<void> begin() override;
    void shutdown() override;
    OperationResult<void> reset() override;
    bool isInitialized() const override { return initialized_; }
    OperationResult<void> healthCheck() const override;
    OperationResult<void> selfTest() const override;

private:
    bool initialized_{false};
};
