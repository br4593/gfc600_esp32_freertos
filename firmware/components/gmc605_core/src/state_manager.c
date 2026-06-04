#include "gmc605/state.h"
#include "gmc605/events.h"
#include "gmc605/modes.h"


void gmc605_set_ready_state(gmc605_state_t* state)
{
    state->system_state = GMC605_SYSTEM_READY;
    state->fd_state = GMC605_FD_OFF;
    state->ap_state = GMC605_AP_OFF;
    state->yd_state = GMC605_YD_OFF;
    state->lat_active_mode = GMC605_LAT_ACTIVE_NONE;
    state->lat_armed_mode = GMC605_LAT_ARMED_NONE;
    state->vert_active_mode = GMC605_VERT_ACTIVE_NONE;
    state->vert_armed_mode = GMC605_VERT_ARMED_NONE;
    state->nav_source = GMC605_NAV_SOURCE_NONE;
    state->selected_heading_deg = 0;
    state->selected_altitude_ft = 0;
    state->selected_vs_fpm = 0;
}


bool gmc605_check_lat_vert_off(gmc605_state_t* state)
{
    return state->lat_active_mode == GMC605_LAT_ACTIVE_NONE && state->vert_active_mode == GMC605_VERT_ACTIVE_NONE;
}

void gmc605_handle_event(gmc605_state_t* state, gmc605_event_t* event)
{
    switch (event->type) {
        case GMC605_EVENT_NONE:
            break;

        case GMC605_EVENT_FD_PRESS:
            if (state->fd_state == GMC605_FD_OFF) {
                state->fd_state = GMC605_FD_ON;
            } else {
                state->fd_state = GMC605_FD_OFF;
            }
            break;

        case GMC605_EVENT_AP_PRESS:
            if (state->ap_state == GMC605_AP_OFF) {
                state->ap_state = GMC605_AP_ON;
                state->fd_state = GMC605_FD_ON; // AP engagement turns on FD
            } else {
                state->ap_state = GMC605_AP_OFF;
            }
            break;

        case GMC605_EVENT_AP_DISCONNECT:
            state->ap_state = GMC605_AP_MANUAL_DISCONNECT;
            break;

        default:
            break;
    }
}


