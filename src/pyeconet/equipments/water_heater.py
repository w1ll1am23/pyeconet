"""EcoNet water heater"""

import logging
from typing import Dict

from pyeconet.equipments import Equipment

_LOGGER = logging.getLogger(__name__)


class WaterHeater(Equipment):

    @property
    def leak_installed(self) -> bool:
        """Return if heater has leak detection or not"""
        return self._equipment_info.get("@LEAKINSTALLED")["value"] == 1

    @property
    def tank_hot_water_capacity(self) -> int:
        """Return the hot water capacity"""
        icon = self._equipment_info.get("@HOTWATER")
        value = 100
        if icon == "ic_tank_hundread_percent.png":
            value = 100
        elif icon == "ic_tank_fourty_percent.png":
            value = 40
        elif icon == "ic_tank_ten_percent.png":
            value = 10
        elif icon == "ic_tank_empty.png":
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
