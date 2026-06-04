#ifndef GMC605_STATE_H
#define GMC605_STATE_H

#include <stdint.h>

#include "gmc605/modes.h"

typedef struct {
    system_state_t system_state;
    fd_state_t fd_state;
    ap_state_t ap_state;
    yd_state_t yd_state;
    lateral_active_mode_t lat_active_mode;
    lateral_armed_mode_t lat_armed_mode;
    vertical_active_mode_t vert_active_mode;
    vertical_armed_mode_t vert_armed_mode;
    nav_source_t nav_source;
    uint16_t selected_heading_deg;
    int32_t selected_altitude_ft;
    int32_t selected_vs_fpm;
} gmc605_state_t;

#endif
