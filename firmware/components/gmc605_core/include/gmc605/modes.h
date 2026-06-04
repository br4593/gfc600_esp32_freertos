#ifndef GMC605_MODES_H
#define GMC605_MODES_H

typedef enum {
    SYSTEM_BOOT = 0,
    SYSTEM_PFT,
    SYSTEM_READY,
    SYSTEM_FAIL,
} system_state_t;

typedef enum {
    FD_OFF = 0,
    FD_ON,
} fd_state_t;

typedef enum {
    AP_OFF = 0,
    AP_ON,
    AP_MANUAL_DISCONNECT,
    AP_AUTOMATIC_DISCONNECT,
    AP_FAIL,
} ap_state_t;

typedef enum {
    YD_OFF = 0,
    YD_ON,
    YD_MANUAL_DISCONNECT,
    YD_FAIL,
} yd_state_t;

typedef enum {
    LAT_ACTIVE_NONE = 0,
    LAT_ACTIVE_ROL,
    LAT_ACTIVE_HDG,
    LAT_ACTIVE_GPS,
    LAT_ACTIVE_VOR,
    LAT_ACTIVE_VAPP,
    LAT_ACTIVE_LOC,
    LAT_ACTIVE_BC,
    LAT_ACTIVE_LVL,
    LAT_ACTIVE_GA,
} lateral_active_mode_t;

typedef enum {
    LAT_ARMED_NONE = 0,
    LAT_ARMED_GPS,
    LAT_ARMED_VOR,
    LAT_ARMED_VAPP,
    LAT_ARMED_LOC,
    LAT_ARMED_BC,
} lateral_armed_mode_t;

typedef enum {
    VERT_ACTIVE_NONE = 0,
    VERT_ACTIVE_PIT,
    VERT_ACTIVE_ALT,
    VERT_ACTIVE_ALTS,
    VERT_ACTIVE_VS,
    VERT_ACTIVE_IAS,
    VERT_ACTIVE_FLC,
    VERT_ACTIVE_VPTH,
    VERT_ACTIVE_ALTV,
    VERT_ACTIVE_GP,
    VERT_ACTIVE_GS,
    VERT_ACTIVE_LVL,
    VERT_ACTIVE_GA,
} vertical_active_mode_t;

typedef enum {
    VERT_ARMED_NONE = 0,
    VERT_ARMED_ALTS,
    VERT_ARMED_ALT,
    VERT_ARMED_VPTH,
    VERT_ARMED_ALTV,
    VERT_ARMED_GP,
    VERT_ARMED_GS,
} vertical_armed_mode_t;

typedef enum {
    NAV_SOURCE_NONE = 0,
    NAV_SOURCE_GPS,
    NAV_SOURCE_VOR,
    NAV_SOURCE_LOC,
} nav_source_t;

typedef enum {
    TRACK_MODE_OFF = 0,
    TRACK_MODE_ACTIVE,
} track_mode_state_t;

typedef enum {
    SMART_GLIDE_OFF = 0,
    SMART_GLIDE_ACTIVE,
} smart_glide_state_t;

typedef enum {
    LOW_BANK_OFF = 0,
    LOW_BANK_ON,
} low_bank_state_t;

typedef enum {
    CWS_RELEASED = 0,
    CWS_HELD,
} cws_state_t;

typedef enum {
    EDM_OFF = 0,
    EDM_ARMED,
    EDM_DELAY,
    EDM_ACTIVE,
    EDM_INHIBITED,
    EDM_OVERRIDDEN,
} edm_state_t;

typedef enum {
    PROTECTION_NONE = 0,
    PROTECTION_MINSPEED,
    PROTECTION_MAXSPEED,
} protection_state_t;

typedef enum {
    ESP_ENABLED = 0,
    ESP_DISABLED,
    ESP_ACTIVE,
    ESP_FAIL,
} esp_state_t;

typedef enum {
    RB_OFF = 0,
    RB_ARMED,
    RB_ACTIVE_LEFT_ENGINE,
    RB_ACTIVE_RIGHT_ENGINE,
    RB_FAIL,
} rudder_bias_state_t;

typedef enum {
    PITCH_TRIM_OK = 0,
    PITCH_TRIM_FAIL,
} pitch_trim_state_t;

typedef enum {
    YAW_TRIM_OK = 0,
    YAW_TRIM_FAIL,
} yaw_trim_state_t;

typedef enum {
    ELEVATOR_MISTRIM_NONE = 0,
    ELEVATOR_MISTRIM_NOSE_UP,
    ELEVATOR_MISTRIM_NOSE_DOWN,
} elevator_mistrim_state_t;

typedef enum {
    AILERON_MISTRIM_NONE = 0,
    AILERON_MISTRIM_LEFT,
    AILERON_MISTRIM_RIGHT,
} aileron_mistrim_state_t;

typedef enum {
    RUDDER_MISTRIM_NONE = 0,
    RUDDER_MISTRIM_LEFT,
    RUDDER_MISTRIM_RIGHT,
} rudder_mistrim_state_t;

typedef enum {
    AIRDATA_OK = 0,
    AIRDATA_FAIL,
} airdata_state_t;

typedef enum {
    ATTITUDE_OK = 0,
    ATTITUDE_FAIL,
} attitude_state_t;

typedef enum {
    LINK_OK = 0,
    LINK_STALE,
    LINK_LOST,
} link_state_t;

typedef enum {
    SIM_DISCONNECTED = 0,
    SIM_CONNECTED,
} sim_state_t;

#endif
