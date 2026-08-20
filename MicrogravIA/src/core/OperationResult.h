#pragma once

#include "core/SystemError.h"

template <typename T>
class OperationResult {
public:
    static OperationResult success(const T& value) {
        return OperationResult(true, value, {});
    }

    static OperationResult failure(SystemErrorCode code, const char* message, std::int32_t detail = 0) {
        return OperationResult(false, T{}, {code, message, detail});
    }

    bool isSuccess() const { return success_; }
    explicit operator bool() const { return success_; }
    const T& value() const { return value_; }
    T& value() { return value_; }
    const SystemError& error() const { return error_; }

private:
    OperationResult(bool success, const T& value, const SystemError& error)
        : success_(success), value_(value), error_(error) {}

    bool success_{false};
    T value_{};
    SystemError error_{};
};

template <>
class OperationResult<void> {
public:
    static OperationResult success() { return OperationResult(true, {}); }

    static OperationResult failure(SystemErrorCode code, const char* message, std::int32_t detail = 0) {
        return OperationResult(false, {code, message, detail});
    }

    bool isSuccess() const { return success_; }
    explicit operator bool() const { return success_; }
    const SystemError& error() const { return error_; }

private:
    OperationResult(bool success, const SystemError& error) : success_(success), error_(error) {}

    bool success_{false};
    SystemError error_{};
};
