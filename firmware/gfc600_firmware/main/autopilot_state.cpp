#include "autopilot_state.hpp"





LateralState& AutopilotState::lateral() {
    return lateral_;
}

const LateralState& AutopilotState::lateral() const {
    return lateral_;
}

VerticalState& AutopilotState::vertical() {
    return vertical_;
}

const VerticalState& AutopilotState::vertical() const {
    return vertical_;
}

void AutopilotState::setApEngaged(bool engaged) {
    ap_engaged_ = engaged;
}

bool AutopilotState::apEngaged() const {
    return ap_engaged_;
}

void AutopilotState::setFdEnabled(bool enabled) {
    fd_enabled_ = enabled;
}

bool AutopilotState::fdEnabled() const {
    return fd_enabled_;
}

void AutopilotState::setYdEngaged(bool engaged) {
    yd_engaged_ = engaged;
}

bool AutopilotState::ydEngaged() const {
    return yd_engaged_;
}

void AutopilotState::setLateralActive(LateralMode mode) {
    lateral_.setActive(mode);
}

void AutopilotState::setLateralArmed(LateralMode mode) {
    lateral_.setArmed(mode);
}

LateralMode AutopilotState::getLateralActive() const {
    return lateral_.getActive();
}

LateralMode AutopilotState::getLateralArmed() const {
    return lateral_.getArmed();
}

void AutopilotState::setVerticalActive(VerticalMode mode) {
    vertical_.setActive(mode);
}

void AutopilotState::setVerticalArmed(VerticalMode mode) {
    vertical_.setArmed(mode);
}

VerticalMode AutopilotState::getVerticalActive() const {
    return vertical_.getActive();
}

VerticalMode AutopilotState::getVerticalArmed() const {
    return vertical_.getArmed();
}
