#include "gmc605/lateral_logic.h"


void gmc605_hdg_state_manager(gmc605_state_t* state)
{
    if (state->lat_active_mode == LAT_ACTIVE_HDG) {
        state->lat_active_mode = LAT_ACTIVE_NONE;
    } else {
        state->lat_active_mode = LAT_ACTIVE_HDG;
    }
}


void gmc605_nav_state_manager(gmc605_state_t* state)
{
    if (state->lat_active_mode == LAT_ACTIVE_VOR || state->lat_active_mode == LAT_ACTIVE_LOC || state->lat_active_mode == LAT_ACTIVE_GPS) {
        state->lat_active_mode = LAT_ACTIVE_NONE;
    } else {
        if (state->nav_source == NAV_SOURCE_GPS) {
            state->lat_active_mode = LAT_ACTIVE_GPS;
        } else if (state->nav_source == NAV_SOURCE_VOR) {
            state->lat_active_mode = LAT_ACTIVE_VOR;
        } else if (state->nav_source == NAV_SOURCE_LOC) {
            state->lat_active_mode = LAT_ACTIVE_LOC;
        }  
    }
}

void gmc605_lateral_handle_event(gmc605_state_t* state, gmc605_event_t* event)
{
    switch (event->type) {
        case GMC605_EVENT_HDG_PRESS:
            gmc605_hdg_state_manager(state);
            break;

        case GMC605_EVENT_NAV_PRESS:
            gmc605_nav_state_manager(state);
            break;

        default:
            break;
    }
}
