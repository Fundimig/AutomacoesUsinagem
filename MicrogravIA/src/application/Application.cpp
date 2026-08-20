#include "application/Application.h"

#include <Arduino.h>
#include <cstdio>

#include "config/FirmwareConfig.h"

Application::Application(
    HardwareManager& hardware,
    ICamera& camera,
    IStartButton& startButton,
    IResetButton& resetButton,
    IDisplay& display,
    IPartIdentifier& partIdentifier,
    const PartCatalog& catalog,
    IMarker& marker)
    : hardware_(hardware),
      camera_(camera),
      startButton_(startButton),
      resetButton_(resetButton),
      display_(display),
      partIdentifier_(partIdentifier),
      catalog_(catalog),
      marker_(marker) {}

void Application::begin() {
    Serial.println("[BOOT] Firmware MicroGrav V0.1");
    auto result = hardware_.begin();
    if (!result) {
        enterError(result.error(), false);
        return;
    }
    display_.show("MICROGRAV AUTO", "INICIANDO...", "", "");

    transitionTo(ApplicationState::SelfTest);
    result = partIdentifier_.begin();
    if (!result) {
        enterError(result.error(), false);
        return;
    }
    result = hardware_.selfTest();
    if (!result) {
        enterError(result.error(), false);
        return;
    }
    result = partIdentifier_.selfTest();
    if (!result) {
        enterError(result.error(), false);
        return;
    }
    result = marker_.selfTest();
    if (!result) {
        enterError(result.error(), false);
        return;
    }
    Serial.println("[HW] Self-test completed");
    transitionTo(ApplicationState::Ready);
}

void Application::update() {
    hardware_.update();

    ResetButtonPressed resetEvent{};
    if (resetButton_.consume(resetEvent)) {
        Serial.println("[BUTTON] RESET");
        handleReset(resetEvent);
    } else {
        StartButtonPressed startEvent{};
        if (startButton_.consume(startEvent)) {
            Serial.println("[BUTTON] START");
            handleStart(startEvent);
        }
    }

    handleMarkingEvent(marker_.poll());
    if (state_ == ApplicationState::Completed &&
        static_cast<std::uint32_t>(millis() - completedAtMs_) >= FirmwareConfig::COMPLETED_DISPLAY_MS) {
        clearIdentification();
        transitionTo(ApplicationState::Ready);
    }
}

void Application::transitionTo(ApplicationState next) {
    if (state_ != next) {
        Serial.printf("[APP] %s -> %s\n", stateName(state_), stateName(next));
        state_ = next;
    }
    renderState();
}

void Application::renderState() {
    char line1[21]{};
    char line2[21]{};
    switch (state_) {
        case ApplicationState::Booting:
            display_.show("MICROGRAV AUTO", "INICIANDO...", "", "");
            break;
        case ApplicationState::SelfTest:
            display_.show("MICROGRAV AUTO", "AUTO TESTE...", "AGUARDE", "");
            break;
        case ApplicationState::Ready:
            display_.show("SISTEMA PRONTO", "COLOQUE A PECA", "PRESSIONE START", "");
            break;
        case ApplicationState::Capturing:
            display_.show("CAPTURANDO...", "", "", "");
            break;
        case ApplicationState::Identifying:
            display_.show("IDENTIFICANDO...", "AGUARDE", "", "");
            break;
        case ApplicationState::WaitingConfirmation:
            std::snprintf(line1, sizeof(line1), "PECA: %s", partIdToString(identification_.partId));
            std::snprintf(line2, sizeof(line2), "CONF: %.1f%%", identification_.confidence * 100.0F);
            display_.show(line1, line2, "START: MARCAR", "RESET: RELER");
            break;
        case ApplicationState::PreparingMarking:
            display_.show("PECA CONFIRMADA", "PROGRAMA NAO", "CONFIGURADO", "RESET: RELER");
            break;
        case ApplicationState::Marking:
            std::snprintf(line1, sizeof(line1), "PECA: %s", partIdToString(identification_.partId));
            display_.show(line1, "MARCANDO...", "", "");
            break;
        case ApplicationState::Verifying:
            display_.show("VERIFICANDO...", "AGUARDE", "", "");
            break;
        case ApplicationState::Completed:
            display_.show("MARCACAO OK", "RETIRE A PECA", "", "");
            break;
        case ApplicationState::Error:
            display_.show("NAO IDENTIFICADA", recoverableError_ ? "RESET: RELER" : "FALHA DE HARDWARE", "", "");
            break;
    }
}

void Application::startIdentificationCycle() {
    clearIdentification();
    transitionTo(ApplicationState::Capturing);
    auto capture = camera_.capture();
    if (!capture) {
        Serial.printf("[CAMERA] Capture failed code=%u detail=%ld\n",
            static_cast<unsigned>(capture.error().code), static_cast<long>(capture.error().detail));
        enterError(capture.error(), true);
        return;
    }
    CapturedImage image = capture.value();
    Serial.printf("[CAMERA] Capture OK %ux%u JPEG=%u bytes\n", image.width, image.height, static_cast<unsigned>(image.size));

    transitionTo(ApplicationState::Identifying);
    auto identified = partIdentifier_.identify(image);
    camera_.release(image);
    if (!identified) {
        Serial.printf("[VISION] Identification failed code=%u detail=%ld\n",
            static_cast<unsigned>(identified.error().code), static_cast<long>(identified.error().detail));
        enterError(identified.error(), true);
        return;
    }
    identification_ = identified.value();
    hasIdentification_ = true;
    Serial.printf("[VISION] %s confidence=%.6f box=%lu,%lu,%lu,%lu\n",
        partIdToString(identification_.partId), identification_.confidence,
        static_cast<unsigned long>(identification_.x), static_cast<unsigned long>(identification_.y),
        static_cast<unsigned long>(identification_.width), static_cast<unsigned long>(identification_.height));
    transitionTo(ApplicationState::WaitingConfirmation);
}

void Application::confirmIdentification() {
    if (!hasIdentification_) {
        enterError({SystemErrorCode::PartNotIdentified, "No identification to confirm", 0}, true);
        return;
    }
    Serial.printf("[APP] Operator confirmed %s\n", partIdToString(identification_.partId));
    transitionTo(ApplicationState::PreparingMarking);
    const auto programResult = catalog_.find(identification_.partId);
    if (!programResult) {
        Serial.println("[MARKING] BLOCKED: program not found");
        return;
    }
    const MarkingProgram& program = *programResult.value();
    if (!program.configured || !program.validatedForProduction) {
        Serial.printf("[MARKING] BLOCKED: %s program configured=%s validatedForProduction=%s\n",
            partIdToString(program.partId), program.configured ? "true" : "false",
            program.validatedForProduction ? "true" : "false");
        return;
    }
    const auto startResult = marker_.start(program);
    if (!startResult) {
        enterError(startResult.error(), false);
        return;
    }
    transitionTo(ApplicationState::Marking);
}

void Application::handleStart(const StartButtonPressed&) {
    if (state_ == ApplicationState::Ready || (state_ == ApplicationState::Error && recoverableError_)) {
        startIdentificationCycle();
    } else if (state_ == ApplicationState::WaitingConfirmation) {
        confirmIdentification();
    } else {
        Serial.printf("[APP] START ignored in %s\n", stateName(state_));
    }
}

void Application::handleReset(const ResetButtonPressed&) {
    if (state_ == ApplicationState::WaitingConfirmation || state_ == ApplicationState::PreparingMarking ||
        (state_ == ApplicationState::Error && recoverableError_)) {
        Serial.println("[APP] Discarding result and forcing a new capture");
        startIdentificationCycle();
    } else {
        Serial.printf("[APP] RESET ignored in %s\n", stateName(state_));
    }
}

void Application::handleMarkingEvent(MarkingEvent event) {
    if (event == MarkingEvent::None) return;
    if (event == MarkingEvent::OutOfArea) {
        enterError({SystemErrorCode::HardwareUnavailable, "Micrograv out of area", 12}, false);
    } else if (event == MarkingEvent::HardwareFault) {
        enterError({SystemErrorCode::HardwareUnavailable, "Micrograv motor or drive fault", 18}, false);
    } else if (event == MarkingEvent::MarkingFinished && state_ == ApplicationState::Marking) {
        transitionTo(ApplicationState::Verifying);
    } else if (event == MarkingEvent::CountFinished && state_ == ApplicationState::Verifying) {
        completedAtMs_ = millis();
        transitionTo(ApplicationState::Completed);
    } else if (event == MarkingEvent::UnknownResponse) {
        Serial.println("[MARKING] Unknown M20 response");
    }
}

void Application::enterError(const SystemError& error, bool recoverable) {
    recoverableError_ = recoverable;
    Serial.printf("[ERROR] code=%u detail=%ld message=%s\n",
        static_cast<unsigned>(error.code), static_cast<long>(error.detail), error.message);
    transitionTo(ApplicationState::Error);
}

void Application::clearIdentification() {
    identification_ = {};
    hasIdentification_ = false;
}

const char* Application::stateName(ApplicationState state) {
    switch (state) {
        case ApplicationState::Booting: return "BOOTING";
        case ApplicationState::SelfTest: return "SELF_TEST";
        case ApplicationState::Ready: return "READY";
        case ApplicationState::Capturing: return "CAPTURING";
        case ApplicationState::Identifying: return "IDENTIFYING";
        case ApplicationState::WaitingConfirmation: return "WAITING_CONFIRMATION";
        case ApplicationState::PreparingMarking: return "PREPARING_MARKING";
        case ApplicationState::Marking: return "MARKING";
        case ApplicationState::Verifying: return "VERIFYING";
        case ApplicationState::Completed: return "COMPLETED";
        case ApplicationState::Error: return "ERROR";
    }
    return "UNKNOWN";
}
