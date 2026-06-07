#pragma once

#include <cstddef>

#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"

class SerialConnector {
public:
    static constexpr std::size_t MAX_LINE_LENGTH = 2048;

    SerialConnector(uart_port_t uart_num, gpio_num_t tx_pin, gpio_num_t rx_pin);

    esp_err_t init();

    // Returns line length, 0 on timeout, or -1 after discarding an overlong line.
    int readLine(char* output, std::size_t output_size, TickType_t timeout_ticks);

private:
    uart_port_t uart_num_;
    gpio_num_t tx_pin_;
    gpio_num_t rx_pin_;

    char line_buffer_[MAX_LINE_LENGTH];
    std::size_t line_length_ = 0;
    bool discarding_overlong_line_ = false;
};
