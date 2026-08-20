#include "hardware/storage/MicroSd.h"

#include <SD_MMC.h>

#include "config/BoardPins.h"

OperationResult<void> MicroSd::begin() {
    if (initialized_) return OperationResult<void>::success();
    SD_MMC.setPins(BoardPins::SD_CLK, BoardPins::SD_CMD, BoardPins::SD_D0);
    initialized_ = SD_MMC.begin("/sdcard", true);
    if (!initialized_) {
        return OperationResult<void>::failure(SystemErrorCode::StorageUnavailable, "microSD unavailable");
    }
    return OperationResult<void>::success();
}

void MicroSd::shutdown() {
    if (initialized_) SD_MMC.end();
    initialized_ = false;
}

OperationResult<void> MicroSd::reset() {
    shutdown();
    return begin();
}

OperationResult<void> MicroSd::healthCheck() const {
    if (!initialized_ || SD_MMC.cardType() == CARD_NONE) {
        return OperationResult<void>::failure(SystemErrorCode::StorageUnavailable, "microSD card not detected");
    }
    return OperationResult<void>::success();
}

OperationResult<void> MicroSd::selfTest() const { return healthCheck(); }
