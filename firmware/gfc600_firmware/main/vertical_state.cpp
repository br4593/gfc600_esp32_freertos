#include "vertical_state.hpp"

void VerticalState::setActive(VerticalMode mode)
{
    active_ = mode;
}

void VerticalState::setArmed(VerticalMode mode)
{
    armed_ = mode;
}

VerticalMode VerticalState::getActive() const
{
    return active_;
}

VerticalMode VerticalState::getArmed() const
{
    return armed_;
}
