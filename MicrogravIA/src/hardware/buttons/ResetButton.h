#pragma once

#include "hardware/buttons/DebouncedButton.h"
#include "hardware/buttons/IResetButton.h"

class ResetButton final : public IResetButton {
public:
    ResetButton();
    OperationResult<void> begin() override;
    void shutdown() override;
    OperationResult<void> reset() override;
    bool isInitialized() const override;
    OperationResult<void> healthCheck() const override;
    OperationResult<void> selfTest() const override;
    void update() override;
    bool consume(ResetButtonPressed& event) override;

private:
    DebouncedButton button_;
};
