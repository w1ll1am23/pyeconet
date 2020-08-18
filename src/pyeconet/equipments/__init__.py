"""Define an EcoNet equipment"""
import logging

from enum import Enum
from typing import Dict, Tuple, Union

_LOGGER = logging.getLogger(__name__)

WATER_HEATER = "WH"
THERMOSTAT = "HVAC"


class EquipmentType(Enum):
    """Define the equipment type"""

    WATER_HEATER = 1
    THERMOSTAT = 2
    UNKNOWN = 99


class Equipment:
    """Define an equipment"""

    def __init__(self, equipment_info: dict, api_interface) -> None:
        self._api = api_interface
        self._equipment_info = equipment_info
        self._update_callback = None

    def set_update_callback(self, callback):
        self._update_callback = callback

    def update_equipment_info(self, update: dict):
        """Take a dictionary and update the stored _equipment_info based on the present dict fields"""
        # Make sure this update is for this device, should probably check this before sending updates however
        _set = False
        if update.get("device_name") == self.device_id:
            for key, value in update.items():
                if key[0] == "@":
                    _LOGGER.debug("Before update %s : %s", key, self._equipment_info.get(key))
                    try:
                        if isinstance(value, Dict):
                            for _key, _value in value.items():
                                self._equipment_info[key][_key] = _value
                                _LOGGER.debug("Updating [%s][%s] = %s", key, _key, _value)
                        else:
                            if isinstance(self._equipment_info.get(key), Dict):
                                if self._equipment_info[key].get("value") is not None:
                                    self._equipment_info[key]["value"] = value
                                    _LOGGER.debug("Updating [%s][value] = %s", key, value)
                            else:
                                self._equipment_info[key] = value
                                _LOGGER.debug("Updating [%s] = %s", key, value)
                    except Exception:
                        _LOGGER.error("Failed to update with message: %s", update)
                    _LOGGER.debug("After update %s : %s", key, self._equipment_info.get(key))
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
    def supports_away(self) -> bool:
        """Return if the user has enabled away mode functionality for this equipment."""
        return self._equipment_info.get("@AWAYCONFIG", False)

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
    def alert_count(self) -> int:
        """Return the number of active alerts"""
        return self._equipment_info.get("@ALERTCOUNT")

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
    def wifi_signal(self) -> Union[int, None]:
        """Return the Wifi signal in db.

        Note: this field isn't present in the REST API and only comes back on the devices MQTT topic.
        That means this field will be None until an update comes through over MQTT.
        """
        signal = self._equipment_info.get("@SIGNAL")
        try:
            if signal:
                signal = int(signal)
        except TypeError:
            if signal:
                signal = self._equipment_info.get("@SIGNAL")["value"]
        return signal

    def force_update_from_api(self):
        self._api.refresh_equipment(self)

    def set_away_mode(self, away):
        """Set the away mode for the equipment"""
        if self.supports_away:
            self._api.publish({"@AWAY": away}, self.device_id, self.serial_number)
        else:
            _LOGGER.error("Unit isn't set up for away mode")
