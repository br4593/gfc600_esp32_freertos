#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "serial_utils.hpp"

SemaphoreHandle_t print_mutex = xSemaphoreCreateMutex();

void print_thread_safe(const char* string) {

    xSemaphoreTake(print_mutex, portMAX_DELAY);
    printf("%s", string);
    xSemaphoreGive(print_mutex);
}