#include "gmc605/lateral_logic.h"

void lateral_logic_handle_event(gmc605_state_t* state, gmc605_event_t* event)
{
    switch (event->type) {
        case GMC605_EVENT_NONE:
            break;

        case GMC605_EVENT_FD_PRESS:
        case GMC605_EVENT_AP_PRESS:
        case GMC605_EVENT_AP_DISCONNECT:
            /* Lateral logic is handled in state_manager.c, so we do nothing here. */
            break;

        default:
            break;
    }
}