#pragma once

enum class LateralMode {
    NONE = 0,
    ROL,
    HDG,
    GPS,
    VOR,
    LOC,
    VAPP,
    BC,
    LVL,
    GA
};

enum class VerticalMode {
    NONE = 0,
    PIT,
    ALT,
    ALTS,
    VS,
    IAS,
    FLC,
    VPTH,
    ALTV,
    GP,
    GS,
    LVL,
    GA
};

bool lateral_mode_from_string(const char* text, LateralMode& mode);
bool vertical_mode_from_string(const char* text, VerticalMode& mode);
const char* lateral_mode_to_string(LateralMode mode);
const char* vertical_mode_to_string(VerticalMode mode);
