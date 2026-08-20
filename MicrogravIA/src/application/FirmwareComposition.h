#pragma once

#include "application/Application.h"
#include "domain/PartCatalog.h"
#include "hardware/HardwareManager.h"
#include "hardware/buttons/ResetButton.h"
#include "hardware/buttons/StartButton.h"
#include "hardware/camera/Ov2640Camera.h"
#include "hardware/display/Lcd20x4Display.h"
#include "hardware/rs232/Rs232.h"
#include "hardware/storage/MicroSd.h"
#include "marking/Marker.h"
#include "marking/MicrogravM20Protocol.h"
#include "vision/EdgeImpulsePartIdentifier.h"

class FirmwareComposition {
public:
    FirmwareComposition();
    void begin();
    void update();

private:
    Ov2640Camera camera_{};
    StartButton startButton_{};
    ResetButton resetButton_{};
    Lcd20x4Display display_{};
    MicroSd microSd_{};
    Rs232 rs232_{};
    HardwareManager hardware_;
    EdgeImpulsePartIdentifier partIdentifier_{};
    PartCatalog catalog_{};
    MicrogravM20Protocol protocol_;
    Marker marker_;
    Application application_;
};
