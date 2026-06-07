#include "serial_connector.hpp"

#include <cstring>

SerialConnector::SerialConnector(
    uart_port_t uart_num,
    gpio_num_t tx_pin,
    gpio_num_t rx_pin)
    : uart_num_(uart_num), tx_pin_(tx_pin), rx_pin_(rx_pin)
{
}

esp_err_t SerialConnector::init()
{
    uart_config_t config = {};
    config.baud_rate = 115200;
    config.data_bits = UART_DATA_8_BITS;
    config.parity = UART_PARITY_DISABLE;
    config.stop_bits = UART_STOP_BITS_1;
    config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    config.source_clk = UART_SCLK_DEFAULT;

    esp_err_t result = uart_param_config(uart_num_, &config);
    if (result != ESP_OK) {
        return result;
    }

    result = uart_set_pin(
        uart_num_,
        tx_pin_,
        rx_pin_,
        UART_PIN_NO_CHANGE,
        UART_PIN_NO_CHANGE);
    if (result != ESP_OK) {
        return result;
    }

    return uart_driver_install(
        uart_num_,
        MAX_LINE_LENGTH * 2,
        0,
        0,
        nullptr,
        0);
}

int SerialConnector::readLine(
    char* output,
    std::size_t output_size,
    TickType_t timeout_ticks)
{
    if (output == nullptr || output_size == 0) {
        return -1;
    }

    uint8_t byte = 0;

    while (true) {
        const int bytes_read = uart_read_bytes(uart_num_, &byte, 1, timeout_ticks);
        if (bytes_read <= 0) {
            return 0;
        }

        if (byte == '\n') {
            if (discarding_overlong_line_) {
                discarding_overlong_line_ = false;
                line_length_ = 0;
                return -1;
            }

            if (line_length_ > 0 && line_buffer_[line_length_ - 1] == '\r') {
                --line_length_;
            }

            if (line_length_ == 0) {
                continue;
            }

            if (line_length_ >= output_size) {
                line_length_ = 0;
                return -1;
            }

            std::memcpy(output, line_buffer_, line_length_);
            output[line_length_] = '\0';

            const int completed_length = static_cast<int>(line_length_);
            line_length_ = 0;
            return completed_length;
        }

        if (discarding_overlong_line_) {
            continue;
        }

        if (line_length_ >= MAX_LINE_LENGTH - 1) {
            discarding_overlong_line_ = true;
            line_length_ = 0;
            continue;
        }

        line_buffer_[line_length_++] = static_cast<char>(byte);
    }
}
