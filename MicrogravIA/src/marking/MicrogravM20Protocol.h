#pragma once

#include <cstdint>

#include "core/OperationResult.h"
#include "domain/MarkingProgram.h"
#include "hardware/rs232/IRS232.h"
#include "marking/ProtocolFrame.h"

enum class MicrogravQueryField : std::uint8_t {
    BlockType,
    Font,
    X,
    Y,
    Radius,
    Angle,
    Spacing,
    Height,
    SerialNumber,
    CircularDirection,
    SerialIncrement,
    Pause,
    MarkingData,
    ProductionLimit,
    ProductionCount
};

enum class MicrogravResponse : std::uint8_t {
    None,
    MarkingFinished,
    CountFinished,
    OutOfArea,
    MotorOrDriveFault,
    Unknown
};

class MicrogravCommandBuilder {
public:
    static constexpr std::uint8_t ESC = 0x1B;
    static constexpr std::uint8_t CAN = 0x18;

    static OperationResult<ProtocolFrame> memoryClear();
    static OperationResult<ProtocolFrame> selectBlock(std::uint8_t block);
    static OperationResult<ProtocolFrame> selectLinear();
    static OperationResult<ProtocolFrame> selectCircular();
    static OperationResult<ProtocolFrame> selectPlot();
    static OperationResult<ProtocolFrame> select2D();
    static OperationResult<ProtocolFrame> selectFont(std::uint8_t font);
    static OperationResult<ProtocolFrame> setX(std::uint16_t tenthsMm);
    static OperationResult<ProtocolFrame> setY(std::uint16_t tenthsMm);
    static OperationResult<ProtocolFrame> setAngle(std::uint16_t angle);
    static OperationResult<ProtocolFrame> setSpacing(std::uint16_t tenthsMm);
    static OperationResult<ProtocolFrame> setHeight(std::uint16_t tenthsMm);
    static OperationResult<ProtocolFrame> setMarkingData(const char* data);
    static OperationResult<ProtocolFrame> nextBlock();
    static OperationResult<ProtocolFrame> reset();
    static OperationResult<ProtocolFrame> start();
    static OperationResult<ProtocolFrame> stop();
    static OperationResult<ProtocolFrame> query(MicrogravQueryField field);
    static OperationResult<void> selfTest();

private:
    static OperationResult<ProtocolFrame> asciiCommand(const char* body);
    static OperationResult<ProtocolFrame> numericCommand(char command, std::uint16_t value);
};

class MicrogravResponseParser {
public:
    MicrogravResponse consume(std::uint8_t byte);
    void reset();

private:
    std::uint8_t buffer_[8]{};
    std::uint8_t length_{0};
};

class MicrogravM20Protocol {
public:
    explicit MicrogravM20Protocol(IRS232& rs232) : rs232_(rs232) {}

    OperationResult<void> selfTest() const;
    OperationResult<void> prepareAndStart(const MarkingProgram& program);
    OperationResult<void> stop();
    MicrogravResponse poll();

private:
    OperationResult<void> send(const OperationResult<ProtocolFrame>& frame);

    IRS232& rs232_;
    MicrogravResponseParser parser_{};
};
