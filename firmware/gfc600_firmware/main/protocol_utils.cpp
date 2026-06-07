#include "protocol_utils.hpp"

#include "autopilot_modes.hpp"
#include "cJSON.h"
#include "serial_utils.hpp"

#include <cstdio>
#include <cstring>

namespace {

const cJSON* required_item(const cJSON* object, const char* name)
{
    const cJSON* item = cJSON_GetObjectItemCaseSensitive(object, name);
    if (item == nullptr) {
        print_thread_safe("Snapshot is missing a required field\n");
    }
    return item;
}

bool read_bool(const cJSON* root, const char* name, bool& value)
{
    const cJSON* item = required_item(root, name);
    if (!cJSON_IsBool(item)) {
        print_thread_safe("Snapshot field has an invalid boolean value\n");
        return false;
    }

    value = cJSON_IsTrue(item);
    return true;
}

bool read_lateral_mode(const cJSON* root, const char* name, LateralMode& mode)
{
    const cJSON* item = required_item(root, name);
    if (!cJSON_IsString(item) || !lateral_mode_from_string(item->valuestring, mode)) {
        print_thread_safe("Snapshot contains an invalid lateral mode\n");
        return false;
    }

    return true;
}

bool read_vertical_mode(const cJSON* root, const char* name, VerticalMode& mode)
{
    const cJSON* item = required_item(root, name);
    if (!cJSON_IsString(item) || !vertical_mode_from_string(item->valuestring, mode)) {
        print_thread_safe("Snapshot contains an invalid vertical mode\n");
        return false;
    }

    return true;
}

bool read_vertical_armed_mode(const cJSON* root, VerticalMode& mode)
{
    const cJSON* array = required_item(root, "vert_armed");
    if (!cJSON_IsArray(array)) {
        print_thread_safe("Snapshot vert_armed field must be an array\n");
        return false;
    }

    const int count = cJSON_GetArraySize(array);
    if (count == 0) {
        mode = VerticalMode::NONE;
        return true;
    }

    if (count != 1) {
        print_thread_safe("Multiple vertical armed modes are not supported yet\n");
        return false;
    }

    const cJSON* item = cJSON_GetArrayItem(array, 0);
    if (!cJSON_IsString(item) || !vertical_mode_from_string(item->valuestring, mode)) {
        print_thread_safe("Snapshot contains an invalid vertical armed mode\n");
        return false;
    }

    return true;
}

bool validate_mode_relationships(const AutopilotState& state)
{
    if (state.apEngaged() && !state.fdEnabled()) {
        print_thread_safe("Invalid snapshot: AP requires FD\n");
        return false;
    }

    if (state.getLateralActive() != LateralMode::NONE &&
        state.getLateralActive() == state.getLateralArmed()) {
        print_thread_safe("Invalid snapshot: lateral mode is both active and armed\n");
        return false;
    }

    if (state.getVerticalActive() != VerticalMode::NONE &&
        state.getVerticalActive() == state.getVerticalArmed()) {
        print_thread_safe("Invalid snapshot: vertical mode is both active and armed\n");
        return false;
    }

    const bool lateral_lvl = state.getLateralActive() == LateralMode::LVL;
    const bool vertical_lvl = state.getVerticalActive() == VerticalMode::LVL;
    const bool lateral_ga = state.getLateralActive() == LateralMode::GA;
    const bool vertical_ga = state.getVerticalActive() == VerticalMode::GA;

    if (lateral_lvl != vertical_lvl || lateral_ga != vertical_ga) {
        print_thread_safe("Invalid snapshot: coupled mode axes do not match\n");
        return false;
    }

    return true;
}

bool parse_snapshot(const cJSON* root, AutopilotState& candidate)
{
    bool ap_engaged = false;
    bool fd_enabled = false;
    bool yd_engaged = false;
    LateralMode lateral_active = LateralMode::NONE;
    LateralMode lateral_armed = LateralMode::NONE;
    VerticalMode vertical_active = VerticalMode::NONE;
    VerticalMode vertical_armed = VerticalMode::NONE;

    if (!read_bool(root, "ap", ap_engaged) ||
        !read_bool(root, "fd", fd_enabled) ||
        !read_bool(root, "yd", yd_engaged) ||
        !read_lateral_mode(root, "lat_active", lateral_active) ||
        !read_lateral_mode(root, "lat_armed", lateral_armed) ||
        !read_vertical_mode(root, "vert_active", vertical_active) ||
        !read_vertical_armed_mode(root, vertical_armed)) {
        return false;
    }

    candidate.setApEngaged(ap_engaged);
    candidate.setFdEnabled(fd_enabled);
    candidate.setYdEngaged(yd_engaged);
    candidate.setLateralActive(lateral_active);
    candidate.setLateralArmed(lateral_armed);
    candidate.setVerticalActive(vertical_active);
    candidate.setVerticalArmed(vertical_armed);

    return validate_mode_relationships(candidate);
}

}  // namespace

SnapshotParseResult parse_json_and_set_autopilot_state(const char* json_str, AutopilotState& state)
{
    if (json_str == nullptr) {
        return SnapshotParseResult::INVALID;
    }

    cJSON* root = cJSON_Parse(json_str);
    if (!cJSON_IsObject(root)) {
        print_thread_safe("Failed to parse JSON object\n");
        cJSON_Delete(root);
        return SnapshotParseResult::INVALID;
    }

    const cJSON* version = required_item(root, "v");
    const cJSON* type = required_item(root, "type");
    if (!cJSON_IsNumber(version) || version->valueint != 1 ||
        !cJSON_IsString(type) || std::strcmp(type->valuestring, "snapshot") != 0) {
        print_thread_safe("Unsupported protocol message\n");
        cJSON_Delete(root);
        return SnapshotParseResult::INVALID;
    }

    AutopilotState candidate;
    const bool valid = parse_snapshot(root, candidate);
    cJSON_Delete(root);

    if (!valid) {
        return SnapshotParseResult::INVALID;
    }

    if (state == candidate) {
        return SnapshotParseResult::UNCHANGED;
    }

    state = candidate;
    return SnapshotParseResult::UPDATED;
}


void print_ap_state(const AutopilotState& state)
{
    char line[256];
    std::snprintf(
        line,
        sizeof(line),
        "AP: %s, FD: %s, YD: %s, Lat Active: %s, Lat Armed: %s, "
        "Vert Active: %s, Vert Armed: %s\n",
        state.apEngaged() ? "ENGAGED" : "DISENGAGED",
        state.fdEnabled() ? "ENABLED" : "DISABLED",
        state.ydEngaged() ? "ENGAGED" : "DISENGAGED",
        lateral_mode_to_string(state.getLateralActive()),
        lateral_mode_to_string(state.getLateralArmed()),
        vertical_mode_to_string(state.getVerticalActive()),
        vertical_mode_to_string(state.getVerticalArmed()));
    print_thread_safe(line);
}
