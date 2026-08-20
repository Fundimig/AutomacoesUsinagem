#pragma once

#include <driver/gpio.h>

namespace BoardPins {

constexpr gpio_num_t CAMERA_XCLK = GPIO_NUM_15;
constexpr gpio_num_t CAMERA_SIOD = GPIO_NUM_4;
constexpr gpio_num_t CAMERA_SIOC = GPIO_NUM_5;
constexpr gpio_num_t CAMERA_D7 = GPIO_NUM_16;
constexpr gpio_num_t CAMERA_D6 = GPIO_NUM_17;
constexpr gpio_num_t CAMERA_D5 = GPIO_NUM_18;
constexpr gpio_num_t CAMERA_D4 = GPIO_NUM_12;
constexpr gpio_num_t CAMERA_D3 = GPIO_NUM_10;
constexpr gpio_num_t CAMERA_D2 = GPIO_NUM_8;
constexpr gpio_num_t CAMERA_D1 = GPIO_NUM_9;
constexpr gpio_num_t CAMERA_D0 = GPIO_NUM_11;
constexpr gpio_num_t CAMERA_VSYNC = GPIO_NUM_6;
constexpr gpio_num_t CAMERA_HREF = GPIO_NUM_7;
constexpr gpio_num_t CAMERA_PCLK = GPIO_NUM_13;

constexpr gpio_num_t SD_CLK = GPIO_NUM_39;
constexpr gpio_num_t SD_CMD = GPIO_NUM_40;
constexpr gpio_num_t SD_D0 = GPIO_NUM_38;

constexpr gpio_num_t I2C_SDA = GPIO_NUM_1;
constexpr gpio_num_t I2C_SCL = GPIO_NUM_2;

// External normally-open pushbuttons: GPIO -> button -> GND.
constexpr gpio_num_t START_BUTTON = GPIO_NUM_14;
constexpr gpio_num_t RESET_BUTTON = GPIO_NUM_21;

// UART1 plus external 3.3 V TTL <-> RS232 transceiver.
constexpr gpio_num_t RS232_TX = GPIO_NUM_41;
constexpr gpio_num_t RS232_RX = GPIO_NUM_42;
constexpr gpio_num_t RS232_CTS = GPIO_NUM_47;
constexpr gpio_num_t RS232_RTS = GPIO_NUM_43;

}  // namespace BoardPins
