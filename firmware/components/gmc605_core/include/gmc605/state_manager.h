#ifndef GMC605_STATE_MANAGER_H
#define GMC605_STATE_MANAGER_H

#include "gmc605/state.h"
#include "gmc605/events.h"
#include "gmc605/modes.h"

void gmc605_set_ready_state(gmc605_state_t* state);
void gmc605_handle_event(gmc605_state_t* state, gmc605_event_t* event);

#endif