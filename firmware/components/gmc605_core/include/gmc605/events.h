#ifndef GMC605_EVENTS_H
#define GMC605_EVENTS_H

#include <stdint.h>

#include "gmc605/modes.h"

typedef enum {
    GMC605_EVENT_NONE = 0,

    // Button events - main controls
    GMC605_EVENT_FD_PRESS,
    GMC605_EVENT_AP_PRESS,
    GMC605_EVENT_AP_DISCONNECT,

    // Button events - lateral controls
    GMC605_EVENT_HDG_PRESS,
    GMC605_EVENT_NAV_PRESS,
    GMC605_EVENT_APR_PRESS,
    GMC605_EVENT_BC_PRESS,

    // Button events - vertical controls
    GMC605_EVENT_VNV_PRESS,
    GMC605_EVENT_IAS_PRESS,
    GMC605_EVENT_VS_PRESS,
    GMC605_EVENT_ALT_PRESS,
    GMC605_EVENT_LVL_PRESS,


    
    GMC605_EVENT_GPS_CAPTURED,
    GMC605_EVENT_ALT_CAPTURE_STARTED,
    GMC605_EVENT_ALT_CAPTURED,

    GMC605_EVENT_NAV_SOURCE_CHANGED,
    GMC605_EVENT_SELECTED_HEADING_CHANGED,
    GMC605_EVENT_SELECTED_ALTITUDE_CHANGED,
    GMC605_EVENT_SELECTED_VS_CHANGED,
} gmc605_event_type_t;

typedef struct {
    gmc605_event_type_t type;

    union {
        gmc605_nav_source_t nav_source;
        uint16_t selected_heading_deg;
        int32_t selected_altitude_ft;
        int32_t selected_vs_fpm;
    } data;
} gmc605_event_t;

#endif
