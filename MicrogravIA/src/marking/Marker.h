#pragma once

#include "marking/IMarker.h"
#include "marking/MicrogravM20Protocol.h"

class Marker final : public IMarker {
public:
    explicit Marker(MicrogravM20Protocol& protocol) : protocol_(protocol) {}
    OperationResult<void> selfTest() const override;
    OperationResult<void> start(const MarkingProgram& program) override;
    OperationResult<void> stop() override;
    MarkingEvent poll() override;

private:
    MicrogravM20Protocol& protocol_;
};
