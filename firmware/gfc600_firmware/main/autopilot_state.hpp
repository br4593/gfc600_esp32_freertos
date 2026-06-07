#pragma once

#include "lateral_state.hpp"
#include "vertical_state.hpp"

class AutopilotState {
public:

    bool operator==(const AutopilotState& other) const 
    {
        return ap_engaged_ == other.ap_engaged_ &&
               fd_enabled_ == other.fd_enabled_ &&
               yd_engaged_ == other.yd_engaged_ &&
               lateral_.getActive() == other.lateral_.getActive() &&
               lateral_.getArmed() == other.lateral_.getArmed() &&
               vertical_.getActive() == other.vertical_.getActive() &&
               vertical_.getArmed() == other.vertical_.getArmed();
    }
    
    LateralState& lateral();
    const LateralState& lateral() const;
    VerticalState& vertical();
    const VerticalState& vertical() const;

    void setApEngaged(bool engaged);
    bool apEngaged() const;
    void setFdEnabled(bool enabled);
    bool fdEnabled() const;
    void setYdEngaged(bool engaged);
    bool ydEngaged() const;

    void setLateralActive(LateralMode mode);
    void setLateralArmed(LateralMode mode);
    LateralMode getLateralActive() const;
    LateralMode getLateralArmed() const;

    void setVerticalActive(VerticalMode mode);
    void setVerticalArmed(VerticalMode mode);
    VerticalMode getVerticalActive() const;
    VerticalMode getVerticalArmed() const;

private:
    bool ap_engaged_ = false;
    bool fd_enabled_ = false;
    bool yd_engaged_ = false;

    LateralState lateral_;
    VerticalState vertical_;
};
