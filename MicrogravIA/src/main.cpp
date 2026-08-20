#include "application/FirmwareComposition.h"

FirmwareComposition firmware;

void setup() {
    firmware.begin();
}

void loop() {
    firmware.update();
}
