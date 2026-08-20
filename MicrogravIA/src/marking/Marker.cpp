#include "marking/Marker.h"

OperationResult<void> Marker::selfTest() const { return protocol_.selfTest(); }
OperationResult<void> Marker::start(const MarkingProgram& program) { return protocol_.prepareAndStart(program); }
OperationResult<void> Marker::stop() { return protocol_.stop(); }

MarkingEvent Marker::poll() {
    switch (protocol_.poll()) {
        case MicrogravResponse::None: return MarkingEvent::None;
        case MicrogravResponse::MarkingFinished: return MarkingEvent::MarkingFinished;
        case MicrogravResponse::CountFinished: return MarkingEvent::CountFinished;
        case MicrogravResponse::OutOfArea: return MarkingEvent::OutOfArea;
        case MicrogravResponse::MotorOrDriveFault: return MarkingEvent::HardwareFault;
        case MicrogravResponse::Unknown: return MarkingEvent::UnknownResponse;
    }
    return MarkingEvent::UnknownResponse;
}
