#pragma once

#include <cstdint>

#include "application/ApplicationState.h"
#include "domain/PartCatalog.h"
#include "hardware/HardwareManager.h"
#include "hardware/buttons/IResetButton.h"
#include "hardware/buttons/IStartButton.h"
#include "hardware/camera/ICamera.h"
#include "hardware/display/IDisplay.h"
#include "marking/IMarker.h"
#include "vision/IPartIdentifier.h"

class Application {
public:
    Application(
        HardwareManager& hardware,
        ICamera& camera,
        IStartButton& startButton,
        IResetButton& resetButton,
        IDisplay& display,
        IPartIdentifier& partIdentifier,
        const PartCatalog& catalog,
        IMarker& marker);

    void begin();
    void update();
    ApplicationState state() const { return state_; }

private:
    void transitionTo(ApplicationState next);
    void renderState();
    void startIdentificationCycle();
    void confirmIdentification();
    void handleStart(const StartButtonPressed& event);
    void handleReset(const ResetButtonPressed& event);
    void handleMarkingEvent(MarkingEvent event);
    void enterError(const SystemError& error, bool recoverable);
    void clearIdentification();
    static const char* stateName(ApplicationState state);

    HardwareManager& hardware_;
    ICamera& camera_;
    IStartButton& startButton_;
    IResetButton& resetButton_;
    IDisplay& display_;
    IPartIdentifier& partIdentifier_;
    const PartCatalog& catalog_;
    IMarker& marker_;

    ApplicationState state_{ApplicationState::Booting};
    PartIdentificationResult identification_{};
    bool hasIdentification_{false};
    bool recoverableError_{false};
    std::uint32_t completedAtMs_{0};
};
