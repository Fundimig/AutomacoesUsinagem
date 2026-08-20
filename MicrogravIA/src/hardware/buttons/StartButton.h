#pragma once

#include "hardware/buttons/DebouncedButton.h"
#include "hardware/buttons/IStartButton.h"

class StartButton final : public IStartButton {
public:
    StartButton();
    OperationResult<void> begin() override;
    void shutdown() override;
    OperationResult<void> reset() override;
    bool isInitialized() const override;
    OperationResult<void> healthCheck() const override;
    OperationResult<void> selfTest() const override;
    void update() override;
    bool consume(StartButtonPressed& event) override;

private:
    DebouncedButton button_;
};
