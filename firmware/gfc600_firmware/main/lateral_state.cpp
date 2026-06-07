#include "lateral_state.hpp"

void LateralState::setActive(LateralMode mode)
{
    active_ = mode;
}

void LateralState::setArmed(LateralMode mode)
{
    armed_ = mode;
}

LateralMode LateralState::getActive() const
{
    return active_;
}

LateralMode LateralState::getArmed() const
{
    return armed_;
}
