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
    def running(self) -> str:
        """Return the equipment running state"""
        return self._equipment_info.get("@RUNNING")