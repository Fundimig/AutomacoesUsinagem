#include "marking/MicrogravM20Protocol.h"

#include <cstdio>
#include <cstring>

namespace {
bool frameEquals(const ProtocolFrame& frame, const std::uint8_t* expected, std::size_t length) {
    return frame.length == length && std::memcmp(frame.bytes.data(), expected, length) == 0;
}
}

OperationResult<ProtocolFrame> MicrogravCommandBuilder::asciiCommand(const char* body) {
    if (body == nullptr) return OperationResult<ProtocolFrame>::failure(SystemErrorCode::InvalidArgument, "Null protocol command");
    const std::size_t bodyLength = std::strlen(body);
    if (bodyLength + 2 > ProtocolFrame::Capacity) {
        return OperationResult<ProtocolFrame>::failure(SystemErrorCode::ProtocolFrameTooLong, "Micrograv frame too long");
    }
    ProtocolFrame frame{};
    frame.bytes[frame.length++] = ESC;
    std::memcpy(frame.bytes.data() + frame.length, body, bodyLength);
    frame.length += bodyLength;
    frame.bytes[frame.length++] = ';';
    return OperationResult<ProtocolFrame>::success(frame);
}

OperationResult<ProtocolFrame> MicrogravCommandBuilder::numericCommand(char command, std::uint16_t value) {
    if (value > 999) {
        return OperationResult<ProtocolFrame>::failure(SystemErrorCode::ProtocolValueOutOfRange, "Micrograv numeric value must be 000..999");
    }
    char body[5]{};
    std::snprintf(body, sizeof(body), "%c%03u", command, static_cast<unsigned>(value));
    return asciiCommand(body);
}

OperationResult<ProtocolFrame> MicrogravCommandBuilder::memoryClear() { return asciiCommand("@"); }

OperationResult<ProtocolFrame> MicrogravCommandBuilder::selectBlock(std::uint8_t block) {
    if (block > 99) return OperationResult<ProtocolFrame>::failure(SystemErrorCode::ProtocolValueOutOfRange, "Block must be 00..99");
    char body[4]{};
    std::snprintf(body, sizeof(body), "B%02u", static_cast<unsigned>(block));
    return asciiCommand(body);
}

OperationResult<ProtocolFrame> MicrogravCommandBuilder::selectLinear() { return asciiCommand("G1"); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::selectCircular() { return asciiCommand("G2"); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::selectPlot() { return asciiCommand("G3"); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::select2D() { return asciiCommand("G5"); }

OperationResult<ProtocolFrame> MicrogravCommandBuilder::selectFont(std::uint8_t font) {
    if (font > 7) return OperationResult<ProtocolFrame>::failure(SystemErrorCode::ProtocolValueOutOfRange, "Font must be 0..7");
    char body[3] = {'H', static_cast<char>('0' + font), '\0'};
    return asciiCommand(body);
}

OperationResult<ProtocolFrame> MicrogravCommandBuilder::setX(std::uint16_t value) { return numericCommand('I', value); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::setY(std::uint16_t value) { return numericCommand('J', value); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::setAngle(std::uint16_t value) { return numericCommand('L', value); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::setSpacing(std::uint16_t value) { return numericCommand('M', value); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::setHeight(std::uint16_t value) { return numericCommand('O', value); }

OperationResult<ProtocolFrame> MicrogravCommandBuilder::setMarkingData(const char* data) {
    if (data == nullptr || data[0] == '\0') {
        return OperationResult<ProtocolFrame>::failure(SystemErrorCode::InvalidArgument, "Marking data is empty");
    }
    const std::size_t length = std::strlen(data);
    if (length + 3 > ProtocolFrame::Capacity) {
        return OperationResult<ProtocolFrame>::failure(SystemErrorCode::ProtocolFrameTooLong, "Marking data too long");
    }
    for (std::size_t index = 0; index < length; ++index) {
        const unsigned char byte = static_cast<unsigned char>(data[index]);
        if (byte == ';' || byte == ESC || byte == CAN) {
            return OperationResult<ProtocolFrame>::failure(SystemErrorCode::InvalidArgument, "Marking data contains protocol delimiter");
        }
    }
    char body[ProtocolFrame::Capacity]{};
    body[0] = 'U';
    std::memcpy(body + 1, data, length + 1);
    return asciiCommand(body);
}

OperationResult<ProtocolFrame> MicrogravCommandBuilder::nextBlock() { return asciiCommand("Z"); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::reset() { return asciiCommand("%"); }
OperationResult<ProtocolFrame> MicrogravCommandBuilder::start() { return asciiCommand("!"); }

OperationResult<ProtocolFrame> MicrogravCommandBuilder::stop() {
    ProtocolFrame frame{};
    frame.bytes[0] = CAN;
    frame.length = 1;
    return OperationResult<ProtocolFrame>::success(frame);
}

OperationResult<ProtocolFrame> MicrogravCommandBuilder::query(MicrogravQueryField field) {
    char code = 0;
    switch (field) {
        case MicrogravQueryField::BlockType: code = 'G'; break;
        case MicrogravQueryField::Font: code = 'H'; break;
        case MicrogravQueryField::X: code = 'I'; break;
        case MicrogravQueryField::Y: code = 'J'; break;
        case MicrogravQueryField::Radius: code = 'K'; break;
        case MicrogravQueryField::Angle: code = 'L'; break;
        case MicrogravQueryField::Spacing: code = 'M'; break;
        case MicrogravQueryField::Height: code = 'O'; break;
        case MicrogravQueryField::SerialNumber: code = 'Q'; break;
        case MicrogravQueryField::CircularDirection: code = 'P'; break;
        case MicrogravQueryField::SerialIncrement: code = 'R'; break;
        case MicrogravQueryField::Pause: code = 'S'; break;
        case MicrogravQueryField::MarkingData: code = 'U'; break;
        case MicrogravQueryField::ProductionLimit: code = '$'; break;
        case MicrogravQueryField::ProductionCount: code = '#'; break;
    }
    char body[3] = {'?', code, '\0'};
    return asciiCommand(body);
}

OperationResult<void> MicrogravCommandBuilder::selfTest() {
    const std::uint8_t memory[] = {ESC, 0x40, 0x3B};
    const std::uint8_t linear[] = {ESC, 0x47, 0x31, 0x3B};
    const std::uint8_t startBytes[] = {ESC, 0x21, 0x3B};
    const std::uint8_t stopBytes[] = {CAN};
    const std::uint8_t block[] = {ESC, 'B', '0', '0', ';'};
    const std::uint8_t x[] = {ESC, 'I', '3', '0', '0', ';'};
    const std::uint8_t data[] = {ESC, 'U', 'T', 'E', 'C', 'N', 'I', 'G', 'R', 'A', 'V', ';'};
    const auto a = memoryClear(); const auto b = selectLinear(); const auto c = start(); const auto d = stop();
    const auto e = selectBlock(0); const auto f = setX(300); const auto g = setMarkingData("TECNIGRAV");
    if (!a || !b || !c || !d || !e || !f || !g ||
        !frameEquals(a.value(), memory, sizeof(memory)) ||
        !frameEquals(b.value(), linear, sizeof(linear)) ||
        !frameEquals(c.value(), startBytes, sizeof(startBytes)) ||
        !frameEquals(d.value(), stopBytes, sizeof(stopBytes)) ||
        !frameEquals(e.value(), block, sizeof(block)) ||
        !frameEquals(f.value(), x, sizeof(x)) ||
        !frameEquals(g.value(), data, sizeof(data))) {
        return OperationResult<void>::failure(SystemErrorCode::SelfTestFailed, "Micrograv command builder self-test failed");
    }
    return OperationResult<void>::success();
}

void MicrogravResponseParser::reset() { length_ = 0; }

MicrogravResponse MicrogravResponseParser::consume(std::uint8_t byte) {
    if (byte == MicrogravCommandBuilder::ESC) {
        length_ = 0;
        buffer_[length_++] = byte;
        return MicrogravResponse::None;
    }
    if (length_ == 0) return MicrogravResponse::None;
    if (length_ >= sizeof(buffer_)) {
        reset();
        return MicrogravResponse::Unknown;
    }
    buffer_[length_++] = byte;
    if (byte != ';') return MicrogravResponse::None;

    MicrogravResponse response = MicrogravResponse::Unknown;
    if (length_ == 5 && buffer_[1] == 'E') {
        if (buffer_[2] == '0' && buffer_[3] == '3') response = MicrogravResponse::MarkingFinished;
        else if (buffer_[2] == '0' && buffer_[3] == '5') response = MicrogravResponse::CountFinished;
        else if (buffer_[2] == '1' && buffer_[3] == '2') response = MicrogravResponse::OutOfArea;
        else if (buffer_[2] == '1' && buffer_[3] == '8') response = MicrogravResponse::MotorOrDriveFault;
    }
    reset();
    return response;
}

OperationResult<void> MicrogravM20Protocol::selfTest() const {
    return MicrogravCommandBuilder::selfTest();
}

OperationResult<void> MicrogravM20Protocol::send(const OperationResult<ProtocolFrame>& frame) {
    if (!frame) return OperationResult<void>::failure(frame.error().code, frame.error().message, frame.error().detail);
    return rs232_.write(frame.value().bytes.data(), frame.value().length);
}

OperationResult<void> MicrogravM20Protocol::prepareAndStart(const MarkingProgram& program) {
    if (!program.configured) {
        return OperationResult<void>::failure(SystemErrorCode::ProgramNotConfigured, "Marking program not configured");
    }
    if (!program.validatedForProduction) {
        return OperationResult<void>::failure(SystemErrorCode::ProgramNotValidated, "Marking program not validated for production");
    }
    auto result = send(MicrogravCommandBuilder::memoryClear()); if (!result) return result;
    result = send(MicrogravCommandBuilder::selectBlock(program.block)); if (!result) return result;
    switch (program.mode) {
        case MarkingMode::Linear: result = send(MicrogravCommandBuilder::selectLinear()); break;
        case MarkingMode::Circular: result = send(MicrogravCommandBuilder::selectCircular()); break;
        case MarkingMode::Plot: result = send(MicrogravCommandBuilder::selectPlot()); break;
        case MarkingMode::DataMatrix2D: result = send(MicrogravCommandBuilder::select2D()); break;
    }
    if (!result) return result;
    result = send(MicrogravCommandBuilder::selectFont(program.font)); if (!result) return result;
    result = send(MicrogravCommandBuilder::setX(program.xTenthsMm)); if (!result) return result;
    result = send(MicrogravCommandBuilder::setY(program.yTenthsMm)); if (!result) return result;
    result = send(MicrogravCommandBuilder::setAngle(program.angle)); if (!result) return result;
    result = send(MicrogravCommandBuilder::setSpacing(program.spacingTenthsMm)); if (!result) return result;
    result = send(MicrogravCommandBuilder::setHeight(program.heightTenthsMm)); if (!result) return result;
    result = send(MicrogravCommandBuilder::setMarkingData(program.markingData.data())); if (!result) return result;
    return send(MicrogravCommandBuilder::start());
}

OperationResult<void> MicrogravM20Protocol::stop() { return send(MicrogravCommandBuilder::stop()); }

MicrogravResponse MicrogravM20Protocol::poll() {
    while (rs232_.available() > 0) {
        const int byte = rs232_.read();
        if (byte < 0) break;
        const auto response = parser_.consume(static_cast<std::uint8_t>(byte));
        if (response != MicrogravResponse::None) return response;
    }
    return MicrogravResponse::None;
}
