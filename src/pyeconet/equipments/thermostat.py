"""EcoNet thermostat"""

import logging
from typing import Tuple

from . import Equipment

_LOGGER = logging.getLogger(__name__)


class Thermostat(Equipment):

    @property
    def beep_enabled(self) -> bool:
        """Return if thermostat beep is enabled or not"""
        beep = self._equipment_info.get("@BEEP")
        if beep is not None:
            return beep["value"] == 1
        else:
            return False

    @property
    def cool_set_point(self) -> int:
        """Return the current cool set point"""
        return self._equipment_info.get("@COOLSETPOINT")["value"]

    @property
    def cool_set_point_limits(self) -> Tuple:
        """Returns a tuple of the lower limit and upper limit for the cool set point"""
        set_point = self._equipment_info.get("@COOLSETPOINT")["constraints"]
        return set_point["lowerLimit"], set_point["upperLimit"]

    @property
    def heat_set_point(self) -> int:
        return self._equipment_info.get("@HEATSETPOINT")["value"]

    @property
    def heat_set_point_limits(self) -> Tuple:
        """Returns a tuple of the lower limit and upper limit for the heat set point"""
        set_point = self._equipment_info.get("@HEATSETPOINT")["constraints"]
        return set_point["lowerLimit"], set_point["upperLimit"]

    @property
    def deadband(self) -> int:
        return self._equipment_info.get("@DEADBAND")["value"]

    @property
    def deadband_set_point_limits(self) -> Tuple:
        """Returns a tuple of the lower limit and upper limit for the cool set point"""
        set_point = self._equipment_info.get("@DEADBAND")["constraints"]
        return set_point["lowerLimit"], set_point["upperLimit"]

    @property
    def dehumidifier_set_point(self) -> int:
        return self._equipment_info.get("@DEHUMSETPOINT")["value"]

    @property
    def dehumidifier_set_point_limits(self) -> Tuple:
        """Returns a tuple of the lower limit and upper limit for the dehumidifier set point"""
        set_point = self._equipment_info.get("@DEHUMSETPOINT")["constraints"]
        return set_point["lowerLimit"], set_point["upperLimit"]

    @property
    def dehumidifier_enabled(self) -> bool:
        return self._equipment_info.get("@DEHUMENABLE")["value"] == 1

    @property
    def fan_speed(self) -> str:
        return self._equipment_info.get("@FANSPEED")["status"]

    @property
    def screen_locked(self) -> bool:
        return self._equipment_info.get("SCREENLOCK")["value"] == 1

