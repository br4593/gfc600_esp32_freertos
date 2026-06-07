#pragma once

#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_err.h"

class Led {
public:
    static constexpr ledc_mode_t MODE = LEDC_LOW_SPEED_MODE;
    static constexpr ledc_timer_t TIMER = LEDC_TIMER_0;
    static constexpr ledc_timer_bit_t RESOLUTION = LEDC_TIMER_13_BIT;
    static constexpr uint32_t PWM_FREQ_HZ = 5000;
    static constexpr uint32_t MAX_DUTY = (1U << 13) - 1U;

    Led(gpio_num_t gpio_num, ledc_channel_t channel = LEDC_CHANNEL_0, bool active_low = false);

    esp_err_t init();
    esp_err_t setDuty(uint32_t duty);
    esp_err_t on();
    esp_err_t off();
    esp_err_t toggle();

    uint32_t duty() const { return duty_; }
    bool isInitialized() const { return initialized_; }

private:
    uint32_t clampDuty(uint32_t duty) const;
    uint32_t toHardwareDuty(uint32_t duty) const;

    gpio_num_t gpio_num_;
    ledc_channel_t channel_;
    bool active_low_;
    bool initialized_ = false;
    uint32_t duty_ = 0;
    uint32_t saved_duty_ = MAX_DUTY;
};
