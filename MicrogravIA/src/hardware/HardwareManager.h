#pragma once

#include "core/OperationResult.h"
#include "hardware/buttons/IResetButton.h"
#include "hardware/buttons/IStartButton.h"
#include "hardware/camera/ICamera.h"
#include "hardware/display/IDisplay.h"
#include "hardware/rs232/IRS232.h"
#include "hardware/storage/IMicroSd.h"

class HardwareManager {
public:
    HardwareManager(
        ICamera& camera,
        IStartButton& startButton,
        IResetButton& resetButton,
        IDisplay& display,
        IMicroSd& microSd,
        IRS232& rs232);

    OperationResult<void> begin();
    void shutdown();
    OperationResult<void> healthCheck() const;
    OperationResult<void> selfTest();
    void update();
    bool storageAvailable() const { return storageAvailable_; }

private:
    ICamera& camera_;
    IStartButton& startButton_;
    IResetButton& resetButton_;
    IDisplay& display_;
    IMicroSd& microSd_;
    IRS232& rs232_;
    bool storageAvailable_{false};
};
