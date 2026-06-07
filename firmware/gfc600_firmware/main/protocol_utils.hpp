#pragma once

#include "autopilot_state.hpp"

enum class SnapshotParseResult {
    INVALID,
    UNCHANGED,
    UPDATED,
};

// Updates state only after a complete protocol-v1 snapshot passes validation.
SnapshotParseResult parse_json_and_set_autopilot_state(const char* json_str, AutopilotState& state);
void print_ap_state(const AutopilotState& state);
