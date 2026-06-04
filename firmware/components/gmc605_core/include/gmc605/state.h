#ifndef GMC605_STATE_H
#define GMC605_STATE_H

#include <stdint.h>

#include "gmc605/modes.h"

typedef struct {
    gmc605_system_state_t system_state;
    gmc605_fd_state_t fd_state;
    gmc605_ap_state_t ap_state;
    gmc605_yd_state_t yd_state;
    gmc605_lateral_active_mode_t lat_active_mode;
    gmc605_lateral_armed_mode_t lat_armed_mode;
    gmc605_vertical_active_mode_t vert_active_mode;
    gmc605_vertical_armed_mode_t vert_armed_mode;
    gmc605_nav_source_t nav_source;
    uint16_t selected_heading_deg;
    int32_t selected_altitude_ft;
    int32_t selected_vs_fpm;
} gmc605_state_t;

#endif
