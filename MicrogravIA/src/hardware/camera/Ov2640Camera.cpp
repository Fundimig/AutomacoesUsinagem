#include "hardware/camera/Ov2640Camera.h"

#include <esp_camera.h>

#include "config/BoardPins.h"

OperationResult<void> Ov2640Camera::begin() {
    if (initialized_) return OperationResult<void>::success();

    camera_config_t config{};
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = BoardPins::CAMERA_D0;
    config.pin_d1 = BoardPins::CAMERA_D1;
    config.pin_d2 = BoardPins::CAMERA_D2;
    config.pin_d3 = BoardPins::CAMERA_D3;
    config.pin_d4 = BoardPins::CAMERA_D4;
    config.pin_d5 = BoardPins::CAMERA_D5;
    config.pin_d6 = BoardPins::CAMERA_D6;
    config.pin_d7 = BoardPins::CAMERA_D7;
    config.pin_xclk = BoardPins::CAMERA_XCLK;
    config.pin_pclk = BoardPins::CAMERA_PCLK;
    config.pin_vsync = BoardPins::CAMERA_VSYNC;
    config.pin_href = BoardPins::CAMERA_HREF;
    config.pin_sccb_sda = BoardPins::CAMERA_SIOD;
    config.pin_sccb_scl = BoardPins::CAMERA_SIOC;
    config.pin_pwdn = -1;
    config.pin_reset = -1;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 4;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

    const esp_err_t error = esp_camera_init(&config);
    if (error != ESP_OK) {
        return OperationResult<void>::failure(
            SystemErrorCode::CameraInitializationFailed, "OV2640 initialization failed", error);
    }
    initialized_ = true;
    return OperationResult<void>::success();
}

void Ov2640Camera::shutdown() {
    if (!initialized_) return;
    esp_camera_deinit();
    initialized_ = false;
}

OperationResult<void> Ov2640Camera::reset() {
    shutdown();
    return begin();
}

OperationResult<void> Ov2640Camera::healthCheck() const {
    return initialized_ ? OperationResult<void>::success()
                        : OperationResult<void>::failure(SystemErrorCode::NotInitialized, "Camera unavailable");
}

OperationResult<void> Ov2640Camera::selfTest() {
    auto image = capture();
    if (!image) return OperationResult<void>::failure(image.error().code, image.error().message, image.error().detail);
    CapturedImage captured = image.value();
    release(captured);
    return OperationResult<void>::success();
}

OperationResult<CapturedImage> Ov2640Camera::capture() {
    if (!initialized_) {
        return OperationResult<CapturedImage>::failure(SystemErrorCode::NotInitialized, "Camera not initialized");
    }
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame == nullptr) {
        return OperationResult<CapturedImage>::failure(SystemErrorCode::CameraCaptureFailed, "Camera capture failed");
    }
    if (frame->buf == nullptr || frame->len == 0 || frame->format != PIXFORMAT_JPEG) {
        esp_camera_fb_return(frame);
        return OperationResult<CapturedImage>::failure(SystemErrorCode::CameraFrameInvalid, "Invalid JPEG frame");
    }

    CapturedImage image{};
    image.data = frame->buf;
    image.size = frame->len;
    image.width = frame->width;
    image.height = frame->height;
    image.format = CapturedImageFormat::Jpeg;
    image.ownerHandle = frame;
    return OperationResult<CapturedImage>::success(image);
}

void Ov2640Camera::release(CapturedImage& image) {
    if (image.ownerHandle != nullptr) {
        esp_camera_fb_return(static_cast<camera_fb_t*>(image.ownerHandle));
    }
    image = {};
}
