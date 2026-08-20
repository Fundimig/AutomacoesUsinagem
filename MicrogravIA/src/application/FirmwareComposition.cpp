#include "application/FirmwareComposition.h"

#include <Arduino.h>

#include "config/FirmwareConfig.h"

FirmwareComposition::FirmwareComposition()
    : hardware_(camera_, startButton_, resetButton_, display_, microSd_, rs232_),
      protocol_(rs232_),
      marker_(protocol_),
      application_(hardware_, camera_, startButton_, resetButton_, display_, partIdentifier_, catalog_, marker_) {}

void FirmwareComposition::begin() {
    Serial.begin(FirmwareConfig::SERIAL_BAUD);
    const std::uint32_t waitStarted = millis();
    while (!Serial && static_cast<std::uint32_t>(millis() - waitStarted) < 1000U) {
        delay(10);
    }
    Serial.println();
    Serial.printf("[BOOT] Chip=%s flash=%u PSRAM=%u freeHeap=%u freePSRAM=%u\n",
        ESP.getChipModel(), ESP.getFlashChipSize(), ESP.getPsramSize(), ESP.getFreeHeap(), ESP.getFreePsram());
    application_.begin();
}

void FirmwareComposition::update() {
    application_.update();
}
