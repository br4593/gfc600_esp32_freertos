#include "led.hpp"

#include "driver/gpio.h"
#include "esp_log.h"

namespace {

constexpr const char* TAG = "Led";

}  // namespace

Led::Led(gpio_num_t gpio_num, ledc_channel_t channel, bool active_low)
    : gpio_num_(gpio_num), channel_(channel), active_low_(active_low)
{
}

uint32_t Led::clampDuty(uint32_t duty) const
{
    return duty > MAX_DUTY ? MAX_DUTY : duty;
}

uint32_t Led::toHardwareDuty(uint32_t duty) const
{
    if (!active_low_) {
        return duty;
    }

    return MAX_DUTY - duty;
}

esp_err_t Led::init()
{
    gpio_reset_pin(gpio_num_);

    ledc_timer_config_t timer_config = {};
    timer_config.speed_mode = MODE;
    timer_config.timer_num = TIMER;
    timer_config.duty_resolution = RESOLUTION;
    timer_config.freq_hz = PWM_FREQ_HZ;
    timer_config.clk_cfg = LEDC_AUTO_CLK;

    esp_err_t err = ledc_timer_config(&timer_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure PWM timer: %s", esp_err_to_name(err));
        return err;
    }

    ledc_channel_config_t channel_config = {};
    channel_config.speed_mode = MODE;
    channel_config.channel = channel_;
    channel_config.timer_sel = TIMER;
    channel_config.gpio_num = gpio_num_;
    channel_config.duty = active_low_ ? MAX_DUTY : 0;
    channel_config.hpoint = 0;

    err = ledc_channel_config(&channel_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure PWM channel: %s", esp_err_to_name(err));
        return err;
    }

    initialized_ = true;
    return setDuty(0);
}

esp_err_t Led::setDuty(uint32_t duty)
{
    if (!initialized_) {
        return ESP_ERR_INVALID_STATE;
    }

    duty_ = clampDuty(duty);

    const uint32_t hardware_duty = toHardwareDuty(duty_);
    esp_err_t err = ledc_set_duty(MODE, channel_, hardware_duty);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set PWM duty: %s", esp_err_to_name(err));
        return err;
    }

    err = ledc_update_duty(MODE, channel_);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to update PWM duty: %s", esp_err_to_name(err));
    }

    return err;
}

esp_err_t Led::on()
{
    return setDuty(MAX_DUTY);
}

esp_err_t Led::off()
{
    if (duty_ != 0) {
        saved_duty_ = duty_;
    }

    return setDuty(0);
}

esp_err_t Led::toggle()
{
    if (duty_ == 0) {
        const uint32_t restore_duty = saved_duty_ == 0 ? MAX_DUTY : saved_duty_;
        return setDuty(restore_duty);
    }

    saved_duty_ = duty_;
    return setDuty(0);
}
