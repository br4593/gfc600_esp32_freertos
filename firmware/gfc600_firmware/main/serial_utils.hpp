#pragma once
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

extern SemaphoreHandle_t print_mutex;

void print_thread_safe(const char* string);