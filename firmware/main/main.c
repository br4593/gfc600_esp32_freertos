#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "gmc605/state_manager.h"
#include "gmc605/events.h"
#include "gmc605/modes.h"


void app_main(void)
{
    gmc605_state_t state;
    gmc605_set_ready_state(&state);

    printf("Initial system state: %d\n", state.system_state);
    printf("Initial FD state: %d\n", state.fd_state);
    printf("Initial AP state: %d\n", state.ap_state);

    vTaskDelay(1000 / portTICK_PERIOD_MS);
    gmc605_event_t fd_press_event = { .type = GMC605_EVENT_FD_PRESS };
    gmc605_handle_event(&state, &fd_press_event);
    printf("After FD press, FD state: %d\n", state.fd_state);

    vTaskDelay(1000 / portTICK_PERIOD_MS);
    gmc605_event_t ap_press_event = { .type = GMC605_EVENT_AP_PRESS };
    gmc605_handle_event(&state, &ap_press_event);
    printf("After AP press, AP state: %d\n", state.ap_state);

    vTaskDelay(1000 / portTICK_PERIOD_MS);
    gmc605_event_t ap_disconnect_event = { .type = GMC605_EVENT_AP_DISCONNECT };
    gmc605_handle_event(&state, &ap_disconnect_event);
    printf("After AP disconnect, AP state: %d\n", state.ap_state);
}
