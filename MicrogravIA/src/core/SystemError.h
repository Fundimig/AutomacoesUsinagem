#pragma once

#include <cstdint>

enum class SystemErrorCode : std::uint16_t {
    None = 0,
    InvalidArgument,
    NotInitialized,
    AlreadyInitialized,
    HardwareUnavailable,
    CameraInitializationFailed,
    CameraCaptureFailed,
    CameraFrameInvalid,
    DisplayInitializationFailed,
    StorageUnavailable,
    Rs232InitializationFailed,
    Rs232WriteFailed,
    VisionAllocationFailed,
    ImageDecodeFailed,
    ImageResizeFailed,
    InferenceFailed,
    PartNotIdentified,
    ConfidenceTooLow,
    ProgramNotFound,
    ProgramNotConfigured,
    ProgramNotValidated,
    ProtocolFrameTooLong,
    ProtocolValueOutOfRange,
    ProtocolInvalidResponse,
    SelfTestFailed
};

struct SystemError {
    constexpr SystemError() = default;
    constexpr SystemError(SystemErrorCode errorCode, const char* errorMessage, std::int32_t errorDetail = 0)
        : code(errorCode), message(errorMessage), detail(errorDetail) {}

    SystemErrorCode code{SystemErrorCode::None};
    const char* message{"OK"};
    std::int32_t detail{0};
};
