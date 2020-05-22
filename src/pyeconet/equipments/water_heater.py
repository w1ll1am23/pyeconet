"""EcoNet water heater"""

import logging
from typing import Dict, List, Tuple

from pyeconet.equipments import Equipment

_LOGGER = logging.getLogger(__name__)


class WaterHeater(Equipment):

    @property
    def leak_installed(self) -> bool:
        """Return if heater has leak detection or not"""
        leak = self._equipment_info.get("@LEAKINSTALLED")
        if leak is not None:
            return leak["value"] == 1
        else:
            return False

    @property
    def has_shutoff_valve(self) -> bool:
        return self._equipment_info.get("@VALVE") is not None

    @property
    def tank_hot_water_availability(self) -> int:
        """Return the hot water availability"""
        icon = self._equipment_info.get("@HOTWATER")
        value = 100
        if icon is None:
            _LOGGER.debug("Tank does not support hot water capacity")
            return value
        if icon == "ic_tank_hundread_percent.png":
            value = 100
        elif icon == "ic_tank_fourty_percent.png":
            value = 40
        elif icon == "ic_tank_ten_percent.png":
            value = 10
        elif icon == "ic_tank_empty.png":
            # Tank is empty when shutoff valve is closed
            value = 0
        else:
            _LOGGER.error("Invalid tank level: %s", icon)
        return value

    @property
    def shutoff_valve_open(self) -> bool:
        """Return if the shutoff valve is open or not"""
        return self._equipment_info.get("@VALVE")["value"] == 0

    @property
    def tank_health(self) -> int:
        """Return the value 0-100? of the tank/heating element health"""
        return self._equipment_info.get("@TANK")

    def _supports_modes(self) -> bool:
        """Return if the system supports modes or not"""
        return self._equipment_info.get("@MODE") is not None

    @property
    def modes(self) -> List[str]:
        """Return a list of supported operation modes"""
        if self._supports_modes():
            return self._equipment_info.get("@MODE")["enumText"]
        else:
            return []

    @property
    def mode(self):
        """Return the current mode"""
        if self._supports_modes():
            return self._equipment_info.get("@MODE")["status"]
        else:
            return None

    @property
    def enabled(self) -> bool:
        """Return the the water heater is enabled or not"""
        return self._equipment_info.get("@ENABLED")["value"] == 1

    @property
    def set_point(self) -> int:
        """Return the water heaters temperature set point"""
        return self._equipment_info.get("@SETPOINT")["value"]

    @property
    def set_point_limits(self) -> Tuple:
        """Returns a tuple of the lower limit and upper limit for the set point"""
        set_point = self._equipment_info.get("@SETPOINT")["constraints"]
        return set_point["lowerLimit"], set_point["upperLimit"]

    @property
    def alert_count(self) -> int:
        """Return the number of active alerts"""
        return self._equipment_info.get("@ALERTCOUNT")

    @property
    def override_status(self) -> str:
        """Return the alert override status"""
        return self._equipment_info.get("@OVERRIDESTATUS")
