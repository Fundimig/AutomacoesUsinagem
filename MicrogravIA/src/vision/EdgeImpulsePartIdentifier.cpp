#include "vision/EdgeImpulsePartIdentifier.h"

#include <Arduino.h>
#include <Micropulsionador_inferencing.h>
#include <cstring>
#include <esp_heap_caps.h>
#include <img_converters.h>

#include "config/FirmwareConfig.h"
#include "edge-impulse-sdk/dsp/image/processing.hpp"

static_assert(EI_CLASSIFIER_INPUT_WIDTH == 160, "DetectaIA2.0 width mismatch");
static_assert(EI_CLASSIFIER_INPUT_HEIGHT == 160, "DetectaIA2.0 height mismatch");
static_assert(EI_CLASSIFIER_RESIZE_MODE == EI_CLASSIFIER_RESIZE_FIT_LONGEST, "DetectaIA2.0 resize mode mismatch");
static_assert(EI_CLASSIFIER_OBJECT_DETECTION == 1, "DetectaIA2.0 must be object detection");
static_assert(EI_HAS_FOMO == 1, "DetectaIA2.0 must be FOMO");

namespace {
constexpr std::size_t MAX_SOURCE_WIDTH = 1600;
constexpr std::size_t MAX_SOURCE_HEIGHT = 1200;
constexpr std::size_t SOURCE_RGB_BYTES = MAX_SOURCE_WIDTH * MAX_SOURCE_HEIGHT * 3;
constexpr std::size_t MODEL_PIXELS = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
constexpr std::size_t MODEL_RGB_BYTES = MODEL_PIXELS * 3;
}

const std::uint8_t* EdgeImpulsePartIdentifier::activeModelRgb_ = nullptr;

OperationResult<void> EdgeImpulsePartIdentifier::begin() {
    if (initialized_) return OperationResult<void>::success();
    sourceRgb_ = static_cast<std::uint8_t*>(heap_caps_malloc(SOURCE_RGB_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    modelRgb_ = static_cast<std::uint8_t*>(heap_caps_malloc(MODEL_RGB_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (sourceRgb_ == nullptr || modelRgb_ == nullptr) {
        shutdown();
        return OperationResult<void>::failure(SystemErrorCode::VisionAllocationFailed, "Vision PSRAM allocation failed");
    }
    initialized_ = true;
    return OperationResult<void>::success();
}

void EdgeImpulsePartIdentifier::shutdown() {
    if (sourceRgb_ != nullptr) heap_caps_free(sourceRgb_);
    if (modelRgb_ != nullptr) heap_caps_free(modelRgb_);
    sourceRgb_ = nullptr;
    modelRgb_ = nullptr;
    activeModelRgb_ = nullptr;
    initialized_ = false;
}

OperationResult<void> EdgeImpulsePartIdentifier::healthCheck() const {
    return initialized_ && sourceRgb_ != nullptr && modelRgb_ != nullptr
               ? OperationResult<void>::success()
               : OperationResult<void>::failure(SystemErrorCode::NotInitialized, "Vision runtime unavailable");
}

OperationResult<void> EdgeImpulsePartIdentifier::selfTest() {
    auto health = healthCheck();
    if (!health) return health;
    std::memset(modelRgb_, 0, MODEL_RGB_BYTES);
    auto result = runModel();
    if (!result && result.error().code != SystemErrorCode::PartNotIdentified) {
        return OperationResult<void>::failure(result.error().code, result.error().message, result.error().detail);
    }
    return OperationResult<void>::success();
}

OperationResult<PartIdentificationResult> EdgeImpulsePartIdentifier::identify(const CapturedImage& image) {
    if (!initialized_) {
        return OperationResult<PartIdentificationResult>::failure(SystemErrorCode::NotInitialized, "Vision not initialized");
    }
    if (image.data == nullptr || image.size == 0 || image.format != CapturedImageFormat::Jpeg ||
        image.width == 0 || image.height == 0 || image.width > MAX_SOURCE_WIDTH || image.height > MAX_SOURCE_HEIGHT) {
        return OperationResult<PartIdentificationResult>::failure(SystemErrorCode::CameraFrameInvalid, "Unsupported camera frame");
    }

    if (!fmt2rgb888(image.data, image.size, PIXFORMAT_JPEG, sourceRgb_)) {
        return OperationResult<PartIdentificationResult>::failure(SystemErrorCode::ImageDecodeFailed, "JPEG to RGB888 failed");
    }

    const int resizeStatus = ei::image::processing::resize_image_using_mode(
        sourceRgb_, image.width, image.height,
        modelRgb_, EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT,
        3, EI_CLASSIFIER_RESIZE_MODE);
    if (resizeStatus != 0) {
        return OperationResult<PartIdentificationResult>::failure(SystemErrorCode::ImageResizeFailed, "FIT_LONGEST resize failed", resizeStatus);
    }
    return runModel();
}

int EdgeImpulsePartIdentifier::getSignalData(std::size_t offset, std::size_t length, float* output) {
    if (activeModelRgb_ == nullptr || output == nullptr || offset + length > MODEL_PIXELS) return -1;
    for (std::size_t index = 0; index < length; ++index) {
        const std::size_t rgbIndex = (offset + index) * 3;
        const std::uint32_t pixel =
            (static_cast<std::uint32_t>(activeModelRgb_[rgbIndex]) << 16) |
            (static_cast<std::uint32_t>(activeModelRgb_[rgbIndex + 1]) << 8) |
            activeModelRgb_[rgbIndex + 2];
        output[index] = static_cast<float>(pixel);
    }
    return 0;
}

OperationResult<PartIdentificationResult> EdgeImpulsePartIdentifier::runModel() {
    activeModelRgb_ = modelRgb_;
    ei::signal_t signal{};
    signal.total_length = MODEL_PIXELS;
    signal.get_data = &EdgeImpulsePartIdentifier::getSignalData;
    ei_impulse_result_t rawResult{};
    const EI_IMPULSE_ERROR error = run_classifier(&signal, &rawResult, false);
    activeModelRgb_ = nullptr;
    if (error != EI_IMPULSE_OK) {
        return OperationResult<PartIdentificationResult>::failure(SystemErrorCode::InferenceFailed, "Edge Impulse run_classifier failed", error);
    }

    const ei_impulse_result_bounding_box_t* best031 = nullptr;
    const ei_impulse_result_bounding_box_t* best045 = nullptr;
    for (std::size_t index = 0; index < rawResult.bounding_boxes_count; ++index) {
        const auto& box = rawResult.bounding_boxes[index];
        if (box.value <= 0.0F || box.label == nullptr) continue;
        if (std::strcmp(box.label, "031") == 0 && (best031 == nullptr || box.value > best031->value)) best031 = &box;
        if (std::strcmp(box.label, "045") == 0 && (best045 == nullptr || box.value > best045->value)) best045 = &box;
    }

    Serial.printf("[VISION] DSP=%lu ms inference=%lu ms post=%lu ms boxes=%u\n",
        static_cast<unsigned long>(rawResult.timing.dsp),
        static_cast<unsigned long>(rawResult.timing.classification),
        static_cast<unsigned long>(rawResult.timing.postprocessing),
        static_cast<unsigned>(rawResult.bounding_boxes_count));

    if (best031 == nullptr && best045 == nullptr) {
        return OperationResult<PartIdentificationResult>::failure(SystemErrorCode::PartNotIdentified, "No FOMO detection");
    }
    if (best031 != nullptr && best045 != nullptr) {
        Serial.printf("[VISION] Multiple classes: 031=%.6f 045=%.6f; selecting higher confidence\n", best031->value, best045->value);
    }
    const auto* selected = best031 == nullptr ? best045
                         : best045 == nullptr ? best031
                         : best031->value >= best045->value ? best031 : best045;
    if (selected->value < FirmwareConfig::MINIMUM_VISION_CONFIDENCE) {
        return OperationResult<PartIdentificationResult>::failure(SystemErrorCode::ConfidenceTooLow, "Vision confidence below application threshold");
    }

    PartIdentificationResult result{};
    result.partId = std::strcmp(selected->label, "031") == 0 ? PartId::Part031 : PartId::Part045;
    result.confidence = selected->value;
    result.x = selected->x;
    result.y = selected->y;
    result.width = selected->width;
    result.height = selected->height;
    return OperationResult<PartIdentificationResult>::success(result);
}
