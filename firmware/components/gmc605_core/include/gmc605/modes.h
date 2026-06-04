#ifndef GMC605_MODES_H
#define GMC605_MODES_H

typedef enum {
    GMC605_SYSTEM_BOOT = 0,
    GMC605_SYSTEM_PFT,
    GMC605_SYSTEM_READY,
    GMC605_SYSTEM_FAIL,
} gmc605_system_state_t;

typedef enum {
    GMC605_FD_OFF = 0,
    GMC605_FD_ON,
} gmc605_fd_state_t;

typedef enum {
    GMC605_AP_OFF = 0,
    GMC605_AP_ON,
    GMC605_AP_MANUAL_DISCONNECT,
    GMC605_AP_AUTOMATIC_DISCONNECT,
    GMC605_AP_FAIL,
} gmc605_ap_state_t;

typedef enum {
    GMC605_YD_OFF = 0,
    GMC605_YD_ON,
    GMC605_YD_MANUAL_DISCONNECT,
    GMC605_YD_FAIL,
} gmc605_yd_state_t;

typedef enum {
    GMC605_LAT_ACTIVE_NONE = 0,
    GMC605_LAT_ACTIVE_ROL,
    GMC605_LAT_ACTIVE_HDG,
    GMC605_LAT_ACTIVE_GPS,
    GMC605_LAT_ACTIVE_VOR,
    GMC605_LAT_ACTIVE_VAPP,
    GMC605_LAT_ACTIVE_LOC,
    GMC605_LAT_ACTIVE_BC,
    GMC605_LAT_ACTIVE_LVL,
    GMC605_LAT_ACTIVE_GA,
} gmc605_lateral_active_mode_t;

typedef enum {
    GMC605_LAT_ARMED_NONE = 0,
    GMC605_LAT_ARMED_GPS,
    GMC605_LAT_ARMED_VOR,
    GMC605_LAT_ARMED_VAPP,
    GMC605_LAT_ARMED_LOC,
    GMC605_LAT_ARMED_BC,
} gmc605_lateral_armed_mode_t;

typedef enum {
    GMC605_VERT_ACTIVE_NONE = 0,
    GMC605_VERT_ACTIVE_PIT,
    GMC605_VERT_ACTIVE_ALT,
    GMC605_VERT_ACTIVE_ALTS,
    GMC605_VERT_ACTIVE_VS,
    GMC605_VERT_ACTIVE_IAS,
    GMC605_VERT_ACTIVE_FLC,
    GMC605_VERT_ACTIVE_VPTH,
    GMC605_VERT_ACTIVE_ALTV,
    GMC605_VERT_ACTIVE_GP,
    GMC605_VERT_ACTIVE_GS,
    GMC605_VERT_ACTIVE_LVL,
    GMC605_VERT_ACTIVE_GA,
} gmc605_vertical_active_mode_t;

typedef enum {
    GMC605_VERT_ARMED_NONE = 0,
    GMC605_VERT_ARMED_ALTS,
    GMC605_VERT_ARMED_ALT,
    GMC605_VERT_ARMED_VPTH,
    GMC605_VERT_ARMED_ALTV,
    GMC605_VERT_ARMED_GP,
    GMC605_VERT_ARMED_GS,
} gmc605_vertical_armed_mode_t;

typedef enum {
    GMC605_NAV_SOURCE_NONE = 0,
    GMC605_NAV_SOURCE_GPS,
    GMC605_NAV_SOURCE_VOR,
    GMC605_NAV_SOURCE_LOC,
} gmc605_nav_source_t;

typedef enum {
    GMC605_TRACK_MODE_OFF = 0,
    GMC605_TRACK_MODE_ACTIVE,
} gmc605_track_mode_state_t;

typedef enum {
    GMC605_SMART_GLIDE_OFF = 0,
    GMC605_SMART_GLIDE_ACTIVE,
} gmc605_smart_glide_state_t;

typedef enum {
    GMC605_LOW_BANK_OFF = 0,
    GMC605_LOW_BANK_ON,
} gmc605_low_bank_state_t;

typedef enum {
    GMC605_CWS_RELEASED = 0,
    GMC605_CWS_HELD,
} gmc605_cws_state_t;

typedef enum {
    GMC605_EDM_OFF = 0,
    GMC605_EDM_ARMED,
    GMC605_EDM_DELAY,
    GMC605_EDM_ACTIVE,
    GMC605_EDM_INHIBITED,
    GMC605_EDM_OVERRIDDEN,
} gmc605_edm_state_t;

typedef enum {
    GMC605_PROTECTION_NONE = 0,
    GMC605_PROTECTION_MINSPEED,
    GMC605_PROTECTION_MAXSPEED,
} gmc605_protection_state_t;

typedef enum {
    GMC605_ESP_ENABLED = 0,
    GMC605_ESP_DISABLED,
    GMC605_ESP_ACTIVE,
    GMC605_ESP_FAIL,
} gmc605_esp_state_t;

typedef enum {
    GMC605_RB_OFF = 0,
    GMC605_RB_ARMED,
    GMC605_RB_ACTIVE_LEFT_ENGINE,
    GMC605_RB_ACTIVE_RIGHT_ENGINE,
    GMC605_RB_FAIL,
} gmc605_rudder_bias_state_t;

typedef enum {
    GMC605_PITCH_TRIM_OK = 0,
    GMC605_PITCH_TRIM_FAIL,
} gmc605_pitch_trim_state_t;

typedef enum {
    GMC605_YAW_TRIM_OK = 0,
    GMC605_YAW_TRIM_FAIL,
} gmc605_yaw_trim_state_t;

typedef enum {
    GMC605_ELEVATOR_MISTRIM_NONE = 0,
    GMC605_ELEVATOR_MISTRIM_NOSE_UP,
    GMC605_ELEVATOR_MISTRIM_NOSE_DOWN,
} gmc605_elevator_mistrim_state_t;

typedef enum {
    GMC605_AILERON_MISTRIM_NONE = 0,
    GMC605_AILERON_MISTRIM_LEFT,
    GMC605_AILERON_MISTRIM_RIGHT,
} gmc605_aileron_mistrim_state_t;

typedef enum {
    GMC605_RUDDER_MISTRIM_NONE = 0,
    GMC605_RUDDER_MISTRIM_LEFT,
    GMC605_RUDDER_MISTRIM_RIGHT,
} gmc605_rudder_mistrim_state_t;

typedef enum {
    GMC605_AIRDATA_OK = 0,
    GMC605_AIRDATA_FAIL,
} gmc605_airdata_state_t;

typedef enum {
    GMC605_ATTITUDE_OK = 0,
    GMC605_ATTITUDE_FAIL,
} gmc605_attitude_state_t;

typedef enum {
    GMC605_LINK_OK = 0,
    GMC605_LINK_STALE,
    GMC605_LINK_LOST,
} gmc605_link_state_t;

typedef enum {
    GMC605_SIM_DISCONNECTED = 0,
    GMC605_SIM_CONNECTED,
} gmc605_sim_state_t;

#endif
