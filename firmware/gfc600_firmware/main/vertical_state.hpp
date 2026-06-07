#pragma once

#include "autopilot_modes.hpp"

class VerticalState {
public:
    void setActive(VerticalMode mode);
    void setArmed(VerticalMode mode);

    VerticalMode getActive() const;
    VerticalMode getArmed() const;

private:
    VerticalMode active_ = VerticalMode::NONE;
    VerticalMode armed_ = VerticalMode::NONE;
};
