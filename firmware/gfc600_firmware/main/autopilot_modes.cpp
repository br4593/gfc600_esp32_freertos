#include "autopilot_modes.hpp"

#include <cstddef>
#include <cstring>

namespace {

struct LateralModeMapping {
    const char* name;
    LateralMode mode;
};

struct VerticalModeMapping {
    const char* name;
    VerticalMode mode;
};

constexpr LateralModeMapping LATERAL_MODE_MAPPINGS[] = {
    {"NONE", LateralMode::NONE},
    {"ROL", LateralMode::ROL},
    {"HDG", LateralMode::HDG},
    {"GPS", LateralMode::GPS},
    {"VOR", LateralMode::VOR},
    {"LOC", LateralMode::LOC},
    {"VAPP", LateralMode::VAPP},
    {"BC", LateralMode::BC},
    {"LVL", LateralMode::LVL},
    {"GA", LateralMode::GA},
};

constexpr VerticalModeMapping VERTICAL_MODE_MAPPINGS[] = {
    {"NONE", VerticalMode::NONE},
    {"PIT", VerticalMode::PIT},
    {"ALT", VerticalMode::ALT},
    {"ALTS", VerticalMode::ALTS},
    {"VS", VerticalMode::VS},
    {"IAS", VerticalMode::IAS},
    {"FLC", VerticalMode::FLC},
    {"VPTH", VerticalMode::VPTH},
    {"ALTV", VerticalMode::ALTV},
    {"GP", VerticalMode::GP},
    {"GS", VerticalMode::GS},
    {"LVL", VerticalMode::LVL},
    {"GA", VerticalMode::GA},
};

template <typename Mapping, typename Mode, std::size_t Size>
bool mode_from_string(const char* text, const Mapping (&mappings)[Size], Mode& mode)
{
    if (text == nullptr) {
        return false;
    }

    for (const Mapping& mapping : mappings) {
        if (std::strcmp(text, mapping.name) == 0) {
            mode = mapping.mode;
            return true;
        }
    }

    return false;
}

}  // namespace

bool lateral_mode_from_string(const char* text, LateralMode& mode)
{
    return mode_from_string(text, LATERAL_MODE_MAPPINGS, mode);
}

bool vertical_mode_from_string(const char* text, VerticalMode& mode)
{
    return mode_from_string(text, VERTICAL_MODE_MAPPINGS, mode);
}

const char* lateral_mode_to_string(LateralMode mode)
{
    for (const LateralModeMapping& mapping : LATERAL_MODE_MAPPINGS) {
        if (mapping.mode == mode) {
            return mapping.name;
        }
    }

    return "UNKNOWN";
}

const char* vertical_mode_to_string(VerticalMode mode)
{
    for (const VerticalModeMapping& mapping : VERTICAL_MODE_MAPPINGS) {
        if (mapping.mode == mode) {
            return mapping.name;
        }
    }

    return "UNKNOWN";
}
