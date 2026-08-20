#pragma once

enum class ApplicationState {
    Booting,
    SelfTest,
    Ready,
    Capturing,
    Identifying,
    WaitingConfirmation,
    PreparingMarking,
    Marking,
    Verifying,
    Completed,
    Error
};
