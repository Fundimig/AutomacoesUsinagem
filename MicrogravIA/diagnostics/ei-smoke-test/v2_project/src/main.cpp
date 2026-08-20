#include <Arduino.h>
#include <Micropulsionador_inferencing.h>
#include <esp32-hal-psram.h>

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace {

constexpr size_t kImageWidth = EI_CLASSIFIER_INPUT_WIDTH;
constexpr size_t kImageHeight = EI_CLASSIFIER_INPUT_HEIGHT;
constexpr size_t kImageChannels = 3;
constexpr size_t kImagePixels = kImageWidth * kImageHeight;
constexpr size_t kImageBytes = kImagePixels * kImageChannels;
constexpr uint32_t kPacketMagic = 0x474D4945U;  // "EIMG", little-endian.
constexpr uint32_t kPayloadTimeoutMs = 120000;
constexpr uint32_t kSyntheticPixel = 0x00808080U;
constexpr uint8_t kSmokeInferenceCount = 10;

static_assert(EI_CLASSIFIER_INPUT_WIDTH == 160,
              "Unexpected DetectaIA2.0 input width");
static_assert(EI_CLASSIFIER_INPUT_HEIGHT == 160,
              "Unexpected DetectaIA2.0 input height");
static_assert(EI_CLASSIFIER_LABEL_COUNT == 2,
              "Unexpected DetectaIA2.0 label count");
static_assert(EI_CLASSIFIER_OBJECT_DETECTION == 1,
              "DetectaIA2.0 must be an object detection model");
static_assert(EI_CLASSIFIER_OBJECT_DETECTION_LAST_LAYER ==
                  EI_CLASSIFIER_LAST_LAYER_FOMO,
              "DetectaIA2.0 must use FOMO");
static_assert(EI_CLASSIFIER_RESIZE_MODE == EI_CLASSIFIER_RESIZE_FIT_LONGEST,
              "DetectaIA2.0 resize mode differs from the audited export");

#pragma pack(push, 1)
struct ImagePacketHeader {
    uint32_t magic;
    uint32_t imageId;
    uint8_t expectedClass;
    uint8_t reserved[3];
    uint32_t payloadLength;
    uint32_t crc32;
};
#pragma pack(pop)

static_assert(sizeof(ImagePacketHeader) == 20,
              "Unexpected image packet header size");

uint8_t *gImageRgb = nullptr;

const char *expectedLabel(uint8_t expectedClass) {
    switch (expectedClass) {
        case 0:
            return "031";
        case 1:
            return "045";
        default:
            return "INVALID";
    }
}

bool modelLabelsAreExpected() {
    return std::strcmp(ei_classifier_inferencing_categories[0], "031") == 0 &&
           std::strcmp(ei_classifier_inferencing_categories[1], "045") == 0;
}

const char *safeResultLabel(const char *label) {
    if (label == ei_classifier_inferencing_categories[0]) {
        return "031";
    }
    if (label == ei_classifier_inferencing_categories[1]) {
        return "045";
    }
    return "INVALID";
}

bool readExact(uint8_t *destination, size_t length, uint32_t timeoutMs) {
    size_t received = 0;
    uint32_t lastProgress = millis();

    while (received < length) {
        const int available = Serial.available();
        if (available > 0) {
            const size_t remaining = length - received;
            const size_t chunk = static_cast<size_t>(available) < remaining
                                     ? static_cast<size_t>(available)
                                     : remaining;
            const size_t count = Serial.readBytes(
                reinterpret_cast<char *>(destination + received), chunk);
            if (count > 0) {
                received += count;
                lastProgress = millis();
            }
        }
        else {
            delay(1);
        }

        if ((millis() - lastProgress) > timeoutMs) {
            return false;
        }
    }

    return true;
}

uint32_t calculateCrc32(const uint8_t *data, size_t length) {
    uint32_t crc = 0xFFFFFFFFU;

    for (size_t index = 0; index < length; ++index) {
        crc ^= data[index];
        for (uint8_t bit = 0; bit < 8; ++bit) {
            const uint32_t mask =
                static_cast<uint32_t>(-static_cast<int32_t>(crc & 1U));
            crc = (crc >> 1) ^ (0xEDB88320U & mask);
        }
    }

    return ~crc;
}

int getSyntheticData(size_t offset, size_t length, float *outBuffer) {
    if (outBuffer == nullptr || offset > kImagePixels ||
        length > (kImagePixels - offset)) {
        return -1;
    }

    for (size_t index = 0; index < length; ++index) {
        outBuffer[index] = static_cast<float>(kSyntheticPixel);
    }
    return EIDSP_OK;
}

int getImageData(size_t offset, size_t length, float *outBuffer) {
    if (gImageRgb == nullptr || outBuffer == nullptr ||
        offset > kImagePixels || length > (kImagePixels - offset)) {
        return -1;
    }

    for (size_t index = 0; index < length; ++index) {
        const size_t rgbIndex = (offset + index) * kImageChannels;
        const uint32_t red = gImageRgb[rgbIndex];
        const uint32_t green = gImageRgb[rgbIndex + 1];
        const uint32_t blue = gImageRgb[rgbIndex + 2];
        outBuffer[index] =
            static_cast<float>((red << 16) | (green << 8) | blue);
    }

    return EIDSP_OK;
}

uint32_t countValidBoxes(const ei_impulse_result_t &result) {
    uint32_t validBoxes = 0;
    for (uint32_t index = 0; index < result.bounding_boxes_count; ++index) {
        if (result.bounding_boxes[index].value > 0.0F) {
            ++validBoxes;
        }
    }
    return validBoxes;
}

bool runSyntheticSmokeTest() {
    const uint32_t heapBefore = ESP.getFreeHeap();
    const uint32_t psramBefore = ESP.getFreePsram();
    bool passed = true;

    Serial.printf(
        "EI_SMOKE_BEGIN|count=%u|heap=%lu|psram=%lu|min_heap=%lu\n",
        static_cast<unsigned>(kSmokeInferenceCount),
        static_cast<unsigned long>(heapBefore),
        static_cast<unsigned long>(psramBefore),
        static_cast<unsigned long>(ESP.getMinFreeHeap()));

    for (uint8_t iteration = 1; iteration <= kSmokeInferenceCount;
         ++iteration) {
        ei::signal_t signal{};
        signal.total_length = kImagePixels;
        signal.get_data = getSyntheticData;

        ei_impulse_result_t result{};
        const EI_IMPULSE_ERROR error = run_classifier(&signal, &result, false);
        const uint32_t heapAfter = ESP.getFreeHeap();
        const uint32_t psramAfter = ESP.getFreePsram();

        Serial.printf(
            "EI_SMOKE|index=%u|error=%d|boxes=%lu|dsp_us=%llu|"
            "inference_us=%llu|postprocess_us=%llu|heap=%lu|psram=%lu|"
            "min_heap=%lu\n",
            static_cast<unsigned>(iteration), static_cast<int>(error),
            static_cast<unsigned long>(error == EI_IMPULSE_OK
                                           ? countValidBoxes(result)
                                           : 0),
            static_cast<unsigned long long>(
                error == EI_IMPULSE_OK ? result.timing.dsp_us : 0),
            static_cast<unsigned long long>(
                error == EI_IMPULSE_OK ? result.timing.classification_us : 0),
            static_cast<unsigned long long>(
                error == EI_IMPULSE_OK ? result.timing.postprocessing_us : 0),
            static_cast<unsigned long>(heapAfter),
            static_cast<unsigned long>(psramAfter),
            static_cast<unsigned long>(ESP.getMinFreeHeap()));

        if (error != EI_IMPULSE_OK) {
            passed = false;
            break;
        }
        delay(25);
    }

    const uint32_t heapAfter = ESP.getFreeHeap();
    const uint32_t psramAfter = ESP.getFreePsram();
    Serial.printf(
        "EI_SMOKE_FINAL|pass=%u|heap_before=%lu|heap_after=%lu|"
        "heap_delta=%lld|psram_before=%lu|psram_after=%lu|"
        "psram_delta=%lld|min_heap=%lu\n",
        passed ? 1U : 0U, static_cast<unsigned long>(heapBefore),
        static_cast<unsigned long>(heapAfter),
        static_cast<long long>(static_cast<int64_t>(heapAfter) - heapBefore),
        static_cast<unsigned long>(psramBefore),
        static_cast<unsigned long>(psramAfter),
        static_cast<long long>(static_cast<int64_t>(psramAfter) - psramBefore),
        static_cast<unsigned long>(ESP.getMinFreeHeap()));
    return passed;
}

void printErrorResult(const ImagePacketHeader &header,
                      const char *status,
                      int errorCode) {
    const uint32_t heap = ESP.getFreeHeap();
    const uint32_t psram = ESP.getFreePsram();
    Serial.printf(
        "EI_RESULT|id=%lu|expected=%s|status=%s|error=%d|raw_boxes=0|"
        "valid_boxes=0|dsp_us=0|inference_us=0|postprocess_us=0|"
        "heap_before=%lu|heap_after=%lu|psram_before=%lu|"
        "psram_after=%lu|min_heap=%lu\n",
        static_cast<unsigned long>(header.imageId),
        expectedLabel(header.expectedClass), status, errorCode,
        static_cast<unsigned long>(heap), static_cast<unsigned long>(heap),
        static_cast<unsigned long>(psram), static_cast<unsigned long>(psram),
        static_cast<unsigned long>(ESP.getMinFreeHeap()));
    Serial.printf("EI_DONE|id=%lu\n",
                  static_cast<unsigned long>(header.imageId));
}

void processImage(const ImagePacketHeader &header) {
    const char *expected = expectedLabel(header.expectedClass);
    const uint32_t heapBefore = ESP.getFreeHeap();
    const uint32_t psramBefore = ESP.getFreePsram();

    ei::signal_t signal{};
    signal.total_length = kImagePixels;
    signal.get_data = getImageData;

    ei_impulse_result_t result{};
    const EI_IMPULSE_ERROR error = run_classifier(&signal, &result, false);
    const uint32_t heapAfter = ESP.getFreeHeap();
    const uint32_t psramAfter = ESP.getFreePsram();

    if (error != EI_IMPULSE_OK) {
        Serial.printf(
            "EI_RESULT|id=%lu|expected=%s|status=EI_ERROR|error=%d|"
            "raw_boxes=0|valid_boxes=0|dsp_us=0|inference_us=0|"
            "postprocess_us=0|heap_before=%lu|heap_after=%lu|"
            "psram_before=%lu|psram_after=%lu|min_heap=%lu\n",
            static_cast<unsigned long>(header.imageId), expected,
            static_cast<int>(error), static_cast<unsigned long>(heapBefore),
            static_cast<unsigned long>(heapAfter),
            static_cast<unsigned long>(psramBefore),
            static_cast<unsigned long>(psramAfter),
            static_cast<unsigned long>(ESP.getMinFreeHeap()));
        Serial.printf("EI_DONE|id=%lu\n",
                      static_cast<unsigned long>(header.imageId));
        return;
    }

    const uint32_t validBoxes = countValidBoxes(result);
    Serial.print("EI_RESULT|id=");
    Serial.print(static_cast<unsigned long>(header.imageId));
    Serial.print("|expected=");
    Serial.print(expected);
    Serial.print("|status=OK|error=0|raw_boxes=");
    Serial.print(static_cast<unsigned long>(result.bounding_boxes_count));
    Serial.print("|valid_boxes=");
    Serial.print(static_cast<unsigned long>(validBoxes));
    Serial.print("|dsp_us=");
    Serial.print(static_cast<unsigned long>(result.timing.dsp_us));
    Serial.print("|inference_us=");
    Serial.print(static_cast<unsigned long>(result.timing.classification_us));
    Serial.print("|postprocess_us=");
    Serial.print(static_cast<unsigned long>(result.timing.postprocessing_us));
    Serial.print("|heap_before=");
    Serial.print(static_cast<unsigned long>(heapBefore));
    Serial.print("|heap_after=");
    Serial.print(static_cast<unsigned long>(heapAfter));
    Serial.print("|psram_before=");
    Serial.print(static_cast<unsigned long>(psramBefore));
    Serial.print("|psram_after=");
    Serial.print(static_cast<unsigned long>(psramAfter));
    Serial.print("|min_heap=");
    Serial.println(static_cast<unsigned long>(ESP.getMinFreeHeap()));

    uint32_t validIndex = 0;
    for (uint32_t index = 0; index < result.bounding_boxes_count; ++index) {
        const ei_impulse_result_bounding_box_t &box =
            result.bounding_boxes[index];
        if (box.value <= 0.0F) {
            continue;
        }

        ++validIndex;
        const char *label = safeResultLabel(box.label);
        Serial.printf(
            "EI_BOX|id=%lu|index=%lu|label=%s|confidence=%.6f|"
            "x=%lu|y=%lu|w=%lu|h=%lu\n",
            static_cast<unsigned long>(header.imageId),
            static_cast<unsigned long>(validIndex), label, box.value,
            static_cast<unsigned long>(box.x),
            static_cast<unsigned long>(box.y),
            static_cast<unsigned long>(box.width),
            static_cast<unsigned long>(box.height));
    }

    Serial.printf("EI_DONE|id=%lu\n",
                  static_cast<unsigned long>(header.imageId));
    Serial.flush();
}

}  // namespace

void setup() {
    Serial.begin(460800);

    const uint32_t serialWaitStarted = millis();
    while (!Serial && (millis() - serialWaitStarted) < 2000) {
        delay(10);
    }

    delay(250);
    Serial.println();
    Serial.println("========================================");
    Serial.println("EDGE IMPULSE FOMO V2 RUNTIME/BATCH TEST");
    Serial.println("========================================");
    Serial.printf("Chip: %s\n", ESP.getChipModel());
    Serial.printf("Flash: %lu bytes\n",
                  static_cast<unsigned long>(ESP.getFlashChipSize()));
    Serial.printf("Heap total: %lu bytes\n",
                  static_cast<unsigned long>(ESP.getHeapSize()));
    Serial.printf("Heap free: %lu bytes\n",
                  static_cast<unsigned long>(ESP.getFreeHeap()));
    Serial.printf("Minimum heap free: %lu bytes\n",
                  static_cast<unsigned long>(ESP.getMinFreeHeap()));
    Serial.printf("PSRAM total: %lu bytes\n",
                  static_cast<unsigned long>(ESP.getPsramSize()));
    Serial.printf("PSRAM free: %lu bytes\n",
                  static_cast<unsigned long>(ESP.getFreePsram()));
    Serial.printf("Model input: %ux%ux1, output grid: 20x20\n",
                  static_cast<unsigned>(kImageWidth),
                  static_cast<unsigned>(kImageHeight));
    Serial.printf("Labels: %s, %s\n",
                  ei_classifier_inferencing_categories[0],
                  ei_classifier_inferencing_categories[1]);
    Serial.println("Resize mode: FIT_LONGEST");

    if (ESP.getPsramSize() == 0) {
        Serial.println("FAIL: PSRAM NOT AVAILABLE");
        Serial.println("EI_BOOT_FAIL|reason=PSRAM_NOT_AVAILABLE");
        return;
    }
    if (!modelLabelsAreExpected()) {
        Serial.println("EI_BOOT_FAIL|reason=UNEXPECTED_LABELS");
        return;
    }
    if (!runSyntheticSmokeTest()) {
        Serial.println("EI_BOOT_FAIL|reason=SMOKE_TEST_FAILED");
        return;
    }

    gImageRgb = static_cast<uint8_t *>(ps_malloc(kImageBytes));
    if (gImageRgb == nullptr) {
        Serial.println("EI_BOOT_FAIL|reason=PSRAM_IMAGE_BUFFER_ALLOCATION");
        return;
    }

    Serial.printf(
        "EI_BUFFER|location=PSRAM|bytes=%u|psram_free=%lu\n",
        static_cast<unsigned>(kImageBytes),
        static_cast<unsigned long>(ESP.getFreePsram()));
    Serial.printf(
        "EI_BATCH_READY|width=%u|height=%u|channels=%u|bytes=%u|"
        "resize=FIT_LONGEST\n",
        static_cast<unsigned>(kImageWidth),
        static_cast<unsigned>(kImageHeight),
        static_cast<unsigned>(kImageChannels),
        static_cast<unsigned>(kImageBytes));
    Serial.flush();
}

void loop() {
    if (gImageRgb == nullptr) {
        delay(1000);
        return;
    }

    if (Serial.available() < static_cast<int>(sizeof(ImagePacketHeader))) {
        delay(1);
        return;
    }

    ImagePacketHeader header{};
    if (!readExact(reinterpret_cast<uint8_t *>(&header), sizeof(header),
                   kPayloadTimeoutMs)) {
        Serial.println("EI_FATAL|reason=HEADER_TIMEOUT");
        return;
    }

    if (header.magic != kPacketMagic) {
        Serial.printf("EI_FATAL|reason=BAD_MAGIC|value=%08lX\n",
                      static_cast<unsigned long>(header.magic));
        return;
    }
    if (header.expectedClass > 1) {
        printErrorResult(header, "INVALID_EXPECTED_CLASS", -1001);
        return;
    }
    if (header.payloadLength != kImageBytes) {
        printErrorResult(header, "INVALID_PAYLOAD_LENGTH", -1002);
        return;
    }
    if (!readExact(gImageRgb, kImageBytes, kPayloadTimeoutMs)) {
        printErrorResult(header, "PAYLOAD_TIMEOUT", -1003);
        return;
    }

    const uint32_t actualCrc32 = calculateCrc32(gImageRgb, kImageBytes);
    if (actualCrc32 != header.crc32) {
        printErrorResult(header, "CRC_MISMATCH", -1004);
        return;
    }

    processImage(header);
}
