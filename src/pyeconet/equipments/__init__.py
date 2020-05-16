"""Define an EcoNet equipment"""
import logging

from enum import Enum

_LOGGER = logging.getLogger(__name__)


class EquipmentType(Enum):
    """Define the equipment type"""

    WH = 1
    TS = 2
    XX = 99


class Equipment:
    """Define an equipment"""

    def __init__(self, equipment_info: dict) -> None:
        self._equipment_info = equipment_info

    def _update_equipment_info(self, update: dict):
        """Take a dictionary and update the stored _equipment_info based on the present dict fields"""
        # Make sure this update is for this device, should probably check this before sending updates however
        if update.get("device_name") == self.device_name and update.get("device_serial_number") == self.serial_number:
            for key, value in update:
                if key[0] == "@":
                    self._equipment_info[key] = value
                else:
                    _LOGGER.debug("Not updating field because it isn't editable: %s, %s", key, value)
                    pass


    @staticmethod
    def _coerce_type_from_string(value: str) -> EquipmentType:
        """Return a proper type from a string input."""
        try:
            return EquipmentType[value]
        except KeyError:
            _LOGGER.error("Unknown equipment type state: %s", value)
            return EquipmentType.XX

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
    def generic_name(self) -> str:
        """Return the gereric name of the equipment"""
        return self._equipment_info.get("@NAME")["value"]

    @property
    def device_name(self) -> str:
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
