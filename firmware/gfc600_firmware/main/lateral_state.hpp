#pragma once
#include "autopilot_modes.hpp"


class LateralState {
  public:
      void setActive(LateralMode mode);
      void setArmed(LateralMode mode);
      LateralMode getActive() const;
      LateralMode getArmed() const;

  private:
      LateralMode active_ = LateralMode::NONE;
      LateralMode armed_ = LateralMode::NONE;
  };