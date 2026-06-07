#include <stdio.h>

#include "autopilot_state.hpp"
#include "protocol_utils.hpp"
#include "serial_connector.hpp"
#include "serial_utils.hpp"

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

namespace {

constexpr TickType_t DISPLAY_SNAPSHOT_TIMEOUT = pdMS_TO_TICKS(500);

struct DisplaySnapshot {
    AutopilotState state;
    TickType_t received_at;
};

AutopilotState autopilot_state;
SerialConnector serial_connector(UART_NUM_0, GPIO_NUM_1, GPIO_NUM_3);
char line_buffer[SerialConnector::MAX_LINE_LENGTH];
QueueHandle_t display_snapshot_queue;

void read_serial_task(void*)
{
    if (serial_connector.init() != ESP_OK) {
        print_thread_safe("Failed to initialize serial connector\n");
        vTaskDelete(nullptr);
    } else {
        print_thread_safe("Serial connector initialized successfully\n");
    }

    while (true) {
        const int line_length =
            serial_connector.readLine(line_buffer, sizeof(line_buffer), portMAX_DELAY);
        if (line_length <= 0) {
            continue;
        }

        const SnapshotParseResult result =
            parse_json_and_set_autopilot_state(line_buffer, autopilot_state);

        // Every valid snapshot proves the link is alive, even when its state is unchanged.
        if (result != SnapshotParseResult::INVALID) {
            DisplaySnapshot snapshot;
            snapshot.state = autopilot_state;
            snapshot.received_at = xTaskGetTickCount();
            xQueueOverwrite(display_snapshot_queue, &snapshot);
        }
    }
}

void display_state_task(void*)
{
    DisplaySnapshot received_snapshot;
    AutopilotState displayed_state;
    bool has_displayed_state = false;
    bool link_stale = false;
    TickType_t last_valid_snapshot = xTaskGetTickCount();

    while (true) {
        const TickType_t elapsed = xTaskGetTickCount() - last_valid_snapshot;
        const TickType_t wait_ticks =
            link_stale
                ? portMAX_DELAY
                : elapsed < DISPLAY_SNAPSHOT_TIMEOUT
                ? DISPLAY_SNAPSHOT_TIMEOUT - elapsed
                : 0;

        const BaseType_t received = xQueueReceive(
            display_snapshot_queue,
            &received_snapshot,
            wait_ticks);

        if (received == pdPASS) {
            last_valid_snapshot = received_snapshot.received_at;

            if (link_stale) {
                print_thread_safe("Connector snapshot link recovered\n");
                link_stale = false;
            }

            if (!has_displayed_state || !(received_snapshot.state == displayed_state)) {
                displayed_state = received_snapshot.state;
                has_displayed_state = true;
                print_ap_state(displayed_state);
            }
        } else if (!link_stale) {
            print_thread_safe("Connector snapshot link stale: no valid snapshot for 500 ms\n");
            link_stale = true;
        }
    }
}

}  // namespace

extern "C" void app_main(void)
{
    vTaskDelay(pdMS_TO_TICKS(1000));
    print_thread_safe("Starting GFC600 Autopilot State Monitor\n");

    display_snapshot_queue = xQueueCreate(1, sizeof(DisplaySnapshot));
    if (display_snapshot_queue == nullptr) {
        print_thread_safe("Failed to create display snapshot queue\n");
        return;
    }

    if (xTaskCreate(display_state_task, "DisplayStateTask", 3072, nullptr, 1, nullptr) != pdPASS) {
        print_thread_safe("Failed to create display state task\n");
        return;
    }

    if (xTaskCreate(read_serial_task, "ReadSerialTask", 4096, nullptr, 2, nullptr) != pdPASS) {
        print_thread_safe("Failed to create serial task\n");
    }
}
