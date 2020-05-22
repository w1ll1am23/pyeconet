"""Define an EcoNet equipment"""
import logging

from enum import Enum
from typing import Dict

_LOGGER = logging.getLogger(__name__)

WATER_HEATER = "WH"
THERMOSTAT = "TS"


class EquipmentType(Enum):
    """Define the equipment type"""

    WATER_HEATER = 1
    THERMOSTAT = 2
    UNKNOWN = 99


class Equipment:
    """Define an equipment"""

    def __init__(self, equipment_info: dict) -> None:
        self._equipment_info = equipment_info
        self._update_callback = None

    def set_update_callback(self, callback):
        self._update_callback = callback

    def _update_equipment_info(self, update: dict):
        """Take a dictionary and update the stored _equipment_info based on the present dict fields"""
        # Make sure this update is for this device, should probably check this before sending updates however
        _set = False
        if update.get("device_name") == self.device_id and update.get("serial_number") == self.serial_number:
            for key, value in update.items():
                if key[0] == "@":
                    _LOGGER.debug("Equipment %s : %s", key, self._equipment_info[key])
                    try:
                        if isinstance(value, Dict):
                            for _key, _value in value.items():
                                self._equipment_info[key][_key] = _value
                        else:
                            if isinstance(self._equipment_info[key], Dict):
                                if self._equipment_info[key].get("value") is not None:
                                    self._equipment_info[key]["value"] = value
                                    _set = True
                            if not _set:
                                self._equipment_info[key] = value
                    except Exception:
                        _LOGGER.error("Failed to update with message: %s", update)
                    _LOGGER.debug("Equipment %s : %s", key, self._equipment_info[key])
                    _set = True
                else:
                    _LOGGER.debug("Not updating field because it isn't editable: %s, %s", key, value)
                    pass

        else:
            _LOGGER.debug("Invalid update for device: %s", update)

        if self._update_callback is not None and _set:
            _LOGGER.debug("Calling the call back to notify updates have occurred")
            self._update_callback()

    @staticmethod
    def _coerce_type_from_string(value: str) -> EquipmentType:
        """Return a proper type from a string input."""
        if value == WATER_HEATER:
            return EquipmentType.WATER_HEATER
        elif value == THERMOSTAT:
            return EquipmentType.THERMOSTAT
        else:
            _LOGGER.error("Unknown equipment type state: %s", value)
            return EquipmentType.UNKNOWN

    @property
    def active(self) -> bool:
        """Return equipment active state"""
        return self._equipment_info.get("@ACTIVE", True)

    @property
    def away(self) -> bool:
        """Return if equipment has been set to away mode"""
        return self._equipment_info.get("@AWAY", False)

    @property
    def connected(self) -> bool:
        """Return if the equipment is connected or not"""
        return self._equipment_info.get("@CONNECTED", True)

    @property
    def device_name(self) -> str:
        """Return the generic name of the equipment"""
        return self._equipment_info.get("@NAME")["value"]

    @property
    def device_id(self) -> str:
        """Return the number name of the equipment"""
        return self._equipment_info.get("device_name")

    @property
    def generic_type(self) -> str:
        """Return the string type of the equipment"""
        return self._equipment_info.get("@TYPE")

    @property
    def vacation(self) -> bool:
        """Return if this equipment has been set up for vacation mode"""
        return self._equipment_info.get("@VACATION")

    @property
    def type(self) -> EquipmentType:
        """Return the EquipmentType of the equipment"""
        return self._coerce_type_from_string(self._equipment_info.get("device_type"))

    @property
    def serial_number(self) -> str:
        """Return the equipment serial number"""
        return self._equipment_info.get("serial_number")

    @property
    def running(self) -> bool:
        """Return if the equipment is running or not"""
        return self._equipment_info.get("@RUNNING") == "Running"
