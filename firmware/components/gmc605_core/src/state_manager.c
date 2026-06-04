#include "gmc605/state.h"
#include "gmc605/events.h"
#include "gmc605/modes.h"


void gmc605_set_ready_state(gmc605_state_t* state)
{
    state->system_state = SYSTEM_READY;
    state->fd_state = FD_OFF;
    state->ap_state = AP_OFF;
    state->yd_state = YD_OFF;
    state->lat_active_mode = LAT_ACTIVE_NONE;
    state->lat_armed_mode = LAT_ARMED_NONE;
    state->vert_active_mode = VERT_ACTIVE_NONE;
    state->vert_armed_mode = VERT_ARMED_NONE;
    state->nav_source = NAV_SOURCE_NONE;
    state->selected_heading_deg = 0;
    state->selected_altitude_ft = 0;
    state->selected_vs_fpm = 0;
}


bool gmc605_check_lat_vert_off(gmc605_state_t* state)
{
    return state->lat_active_mode == LAT_ACTIVE_NONE && state->vert_active_mode == VERT_ACTIVE_NONE;
}

// This function manages the Flight Director state and related modes when the FD button is pressed.
void gmc605_fd_state_manager(gmc605_state_t* state)
{
    if (state->fd_state == FD_OFF) {
        state->fd_state = FD_ON;
        state->lat_active_mode = LAT_ACTIVE_ROL;
        state->vert_active_mode = VERT_ACTIVE_PIT;
    } else {
        state->fd_state = FD_OFF;
    }

}

void gmc605_ap_state_manager(gmc605_state_t* state)
{
    if (state->ap_state == AP_OFF) {
        state->ap_state = AP_ON;
        state->fd_state = FD_ON; // AP engagement turns on FD
    } else if (state->ap_state == AP_ON) {
        state->ap_state = AP_OFF;
    } else {
        state->ap_state = AP_OFF;
    }
}


void gmc605_lvl_state_manager(gmc605_state_t* state)
{
    if (state->lat_active_mode == LAT_ACTIVE_LVL) {
        state->lat_active_mode = LAT_ACTIVE_NONE;
        state->vert_active_mode = VERT_ACTIVE_NONE;
    } else {
        state->lat_active_mode = LAT_ACTIVE_LVL;
        state->vert_active_mode = VERT_ACTIVE_LVL;
        state->ap_state = AP_ON; // LVL mode requires AP to be on
        state->fd_state = FD_ON; // LVL mode also turns on FD
    }
}

void gmc605_handle_event(gmc605_state_t* state, gmc605_event_t* event)
{
    switch (event->type) {
        case GMC605_EVENT_NONE:
            break;

        case GMC605_EVENT_FD_PRESS:
            gmc605_fd_state_manager(state);
            break;

        case GMC605_EVENT_AP_PRESS:
            if (state->ap_state == AP_OFF) {
                state->ap_state = AP_ON;
                state->fd_state = FD_ON; // AP engagement turns on FD
            } else {
                state->ap_state = AP_OFF;
            }
            break;

        case GMC605_EVENT_LVL_PRESS:
            gmc605_lvl_state_manager(state);
            break;

        case GMC605_EVENT_AP_DISCONNECT:
            state->ap_state = AP_MANUAL_DISCONNECT;
            break;

        default:
            break;
    }
}
