"""EcoNet water heater"""

from datetime import datetime
import logging
import enum
from typing import List, Union, Optional, Dict

from pyeconet.errors import InvalidResponseFormat
from pyeconet.equipment import Equipment

_LOGGER = logging.getLogger(__name__)

try:
    from enum import StrEnum
except ImportError:

    class StrEnum(str, enum.Enum):
        pass


@enum.unique
class WaterHeaterOperationMode(enum.IntEnum):
    """Define the operation mode"""

    OFF = 1
    ELECTRIC_MODE = 2
    ENERGY_SAVING = 3
    HEAT_PUMP_ONLY = 4
    HIGH_DEMAND = 5
    GAS = 6
    ENERGY_SAVER = 7
    PERFORMANCE = 8
    VACATION = 9
    ELECTRIC = 10
    HEAT_PUMP = 11
    ELECTRIC_GAS = 12
    UNKNOWN = 99

    @staticmethod
    def by_string(str_value: str):
        """Convert a string to a supported OperationMode"""
        _cleaned_string = str_value.rstrip().replace(" ", "_").replace("/", "_").upper()
        if _cleaned_string == WaterHeaterOperationMode.OFF.name.upper():
            return WaterHeaterOperationMode.OFF
        elif _cleaned_string == WaterHeaterOperationMode.ELECTRIC_MODE.name.upper():
            return WaterHeaterOperationMode.ELECTRIC_MODE
        elif _cleaned_string == WaterHeaterOperationMode.ENERGY_SAVING.name.upper():
            return WaterHeaterOperationMode.ENERGY_SAVING
        elif _cleaned_string == WaterHeaterOperationMode.HEAT_PUMP_ONLY.name.upper():
            return WaterHeaterOperationMode.HEAT_PUMP_ONLY
        elif _cleaned_string == WaterHeaterOperationMode.HIGH_DEMAND.name.upper():
            return WaterHeaterOperationMode.HIGH_DEMAND
        elif _cleaned_string == WaterHeaterOperationMode.GAS.name.upper():
            return WaterHeaterOperationMode.GAS
        elif _cleaned_string == WaterHeaterOperationMode.ENERGY_SAVER.name.upper():
            # Treat ENERGY SAVER and ENERGY SAVING modes the same
            return WaterHeaterOperationMode.ENERGY_SAVING
        elif _cleaned_string == WaterHeaterOperationMode.PERFORMANCE.name.upper():
            return WaterHeaterOperationMode.PERFORMANCE
        elif _cleaned_string == WaterHeaterOperationMode.VACATION.name.upper():
            return WaterHeaterOperationMode.VACATION
        elif _cleaned_string == WaterHeaterOperationMode.ELECTRIC.name.upper():
            # Treat ELECTRIC MODE and ELECTRIC modes the same
            return WaterHeaterOperationMode.ELECTRIC_MODE
        elif _cleaned_string == WaterHeaterOperationMode.HEAT_PUMP.name.upper():
            # Treat HEAT PUMP ONLY and HEAT PUMP modes the same
            return WaterHeaterOperationMode.HEAT_PUMP_ONLY
        elif _cleaned_string == WaterHeaterOperationMode.ELECTRIC_GAS.name.upper():
            return WaterHeaterOperationMode.ELECTRIC_GAS
        else:
            _LOGGER.error("Unknown mode: [%s]", str_value)
            return WaterHeaterOperationMode.UNKNOWN


@enum.unique
class UsageFormat(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    YEARLY = "yearly"
    MONTHLY = "monthly"


class WaterHeater(Equipment):
    def __init__(self, equipment_info: dict, api_interface) -> None:
        """Initialize."""
        super().__init__(equipment_info, api_interface)
        self._energy_usage = None
        self._historical_energy_usage = None
        self._energy_type = None
        self.water_usage = None

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
    def running(self) -> bool:
        """Return if the water heater is running or not"""
        return self._equipment_info.get("@RUNNING") != ""

    @property
    def running_state(self) -> str:
        """Return the raw running value"""
        return self._equipment_info.get("@RUNNING")

    @property
    def tank_hot_water_availability(self) -> Union[int, None]:
        """Return the hot water availability"""
        icon = self._equipment_info.get("@HOTWATER")
        value = 100
        if icon is None:
            _LOGGER.debug("Tank does not support hot water capacity")
            return None
        if "ic_tank_hundread_percent" in icon:
            value = 100
        elif "ic_tank_fourty_percent" in icon:
            value = 40
        elif "ic_tank_ten_percent" in icon:
            value = 10
        elif "ic_tank_empty" in icon or "ic_tank_zero_percent" in icon:
            # Tank is empty when shutoff valve is closed
            value = 0
        else:
            _LOGGER.error("Invalid tank level: %s", icon)
        return value

    @property
    def shutoff_valve_open(self) -> Union[bool, None]:
        """Return if the shutoff valve is open or not"""
        if self.has_shutoff_valve:
            return self._equipment_info.get("@VALVE")["value"] == 0
        return None

    @property
    def tank_health(self) -> Union[int, None]:
        """Return the value 0-100? of the tank/heating element health"""
        return self._equipment_info.get("@TANK", {}).get("value")

    @property
    def compressor_health(self) -> Union[int, None]:
        """Return the value 0-100 of the compressor for heat pump units health"""
        return self._equipment_info.get("@COMBUSTION", {}).get("value")

    @property
    def demand_response_over(self) -> bool:
        """Return if the demand response is running or not"""
        return self._equipment_info.get("@VALVE")["value"] == 0

    def _supports_modes(self) -> bool:
        """Return if the system supports modes or not"""
        return self._equipment_info.get("@MODE") is not None

    def _supports_on_off(self) -> bool:
        """Return if the system supports on and off"""
        return self._equipment_info.get("@ENABLED") is not None

    @property
    def modes(self) -> List[WaterHeaterOperationMode]:
        """Return a list of supported operation modes"""
        _supported_modes = []
        if self._supports_modes():
            _modes = self._equipment_info.get("@MODE")["constraints"]["enumText"]
            for _mode in _modes:
                _op_mode = WaterHeaterOperationMode.by_string(_mode)
                if _op_mode is not WaterHeaterOperationMode.UNKNOWN:
                    if _op_mode is WaterHeaterOperationMode.ELECTRIC_GAS:
                        if (
                            self.generic_type == "gasWaterHeater"
                            or self.generic_type == "tanklessWaterHeater"
                        ):
                            _supported_modes.append(WaterHeaterOperationMode.GAS)
                        else:
                            _supported_modes.append(
                                WaterHeaterOperationMode.ELECTRIC_MODE
                            )
                    else:
                        _supported_modes.append(_op_mode)
        if self._supports_on_off() and not _supported_modes:
            _supported_modes.append(WaterHeaterOperationMode.OFF)
            if (
                self.generic_type == "gasWaterHeater"
                or self.generic_type == "tanklessWaterHeater"
            ):
                _supported_modes.append(WaterHeaterOperationMode.GAS)
            else:
                _supported_modes.append(WaterHeaterOperationMode.ELECTRIC_MODE)
        elif self._supports_on_off() and _supported_modes:
            _supported_modes.append(WaterHeaterOperationMode.OFF)
        return _supported_modes

    @property
    def mode(self) -> Union[WaterHeaterOperationMode, None]:
        """Return the current mode"""
        if self._supports_on_off():
            if not self.enabled:
                return WaterHeaterOperationMode.OFF
        if self._supports_modes():
            return self.modes[self._equipment_info.get("@MODE")["value"]]
        else:
            if (
                self.generic_type == "gasWaterHeater"
                or self.generic_type == "tanklessWaterHeater"
            ):
                return WaterHeaterOperationMode.GAS
            else:
                return WaterHeaterOperationMode.ELECTRIC_MODE

    @property
    def enabled(self) -> Union[bool, None]:
        """Return the the water heater is enabled or not"""
        if self._supports_modes():
            return self.modes[self._equipment_info.get("@MODE")["value"]] != "OFF"
        elif self._supports_on_off():
            return self._equipment_info.get("@ENABLED")["value"] == 1
        else:
            # Unit doesn't support on/off or modes
            return None

    @property
    def override_status(self) -> str:
        """Return the alert override status"""
        return self._equipment_info.get("@OVERRIDESTATUS")

    @property
    def energy_usage(self) -> Dict[int, float]:
        return self._energy_usage

    @property
    def historical_energy_usage(self) -> Dict[int, float]:
        return self._historical_energy_usage

    @property
    def energy_type(self) -> str:
        """Return the energy type returned from the energy usage response."""
        return self._energy_type

    @property
    def todays_energy_usage(self) -> Union[float, None]:
        _total = 0
        if self._energy_usage:
            for value in self._energy_usage.values():
                _total += value
            return _total    
        else:
            return None

    @property
    def todays_water_usage(self) -> Union[float, None]:
        return self.water_usage

    async def get_energy_usage(
        self,
        usage_format: UsageFormat = UsageFormat.DAILY,
        year: Optional[int] = None,
        month: Optional[int] = None,
        period: Optional[int] = None,
    ):
        """Call dynamic action for energy usage."""
        date = datetime.now()

        if year is None:
            year = date.year

        if month is None:
            month = date.month

        if period is None:
            if usage_format in {"usage", "yearly"}:
                period = 1
            else:
                period = date.day

        payload = {
            "ACTION": "waterheaterUsageReportView",
            "device_name": f"{self.device_id}",
            "serial_number": f"{self.serial_number}",
            "graph_data": {
                "format": f"{usage_format}",
                "month": month,
                "period": period,
                "year": year,
            },
            "usage_type": "energyUsage",
        }
        try:
            _response = await self._api.get_dynamic_action(payload)
        except InvalidResponseFormat:
            _LOGGER.debug("Tried to get energy usage, but unit doesn't support it.")
            return
        self._energy_usage = {
            int(item["name"]): item["value"]
            for item in _response["results"]["energy_usage"]["data"]
        }
        self._historical_energy_usage = {
            int(item["name"]): item["value"]
            for item in _response["results"]["energy_usage"]["historyData"]
        }

        try:
            self._energy_type = (
                _response["results"]["energy_usage"]["message"].split(" ")[3].upper()
            )
        except (KeyError, IndexError):
            _LOGGER.error("Failed to determine energy type from response.")
            if self.generic_type == "gasWaterHeater":
                self._energy_type = "KBTU"
            else:
                self._energy_type = "KWH"

        _LOGGER.debug(self._energy_usage)

    async def get_water_usage(self):
        """Call dynamic action for water usage."""
        date = datetime.now()
        payload = {
            "ACTION": "waterheaterUsageReportView",
            "device_name": f"{self.device_id}",
            "serial_number": f"{self.serial_number}",
            "graph_data": {
                "format": "daily",
                "month": f"{date.month}",
                "period": f"{date.day}",
                "year": f"{date.year}",
            },
            "usage_type": "waterUsage",
        }
        try:
            _response = await self._api.get_dynamic_action(payload)
        except InvalidResponseFormat:
            _LOGGER.debug("Tried to get water usage, but unit doesn't support it.")
            return
        _todays_usage = 0
        for value in _response["results"]["water_usage"]["data"]:
            _todays_usage += value["value"]
        self.water_usage = _todays_usage
        _LOGGER.debug(_todays_usage)

    def set_mode(self, new_mode: WaterHeaterOperationMode):
        """Set the provided mode or enable/disable if mode isn't support."""
        payload = {}

        if not (self._supports_on_off() or self._supports_modes()):
            _LOGGER.error(
                "Unit doesn't support on off or modes, shouldn't be trying to set a mode."
            )
            return

        if self._supports_on_off():
            if new_mode == WaterHeaterOperationMode.OFF:
                payload["@ENABLED"] = 0
            else:
                payload["@ENABLED"] = 1

        # Traverse the supported mode strings returned from the water heater
        # and set the payload to the index value of the one we want
        if self._supports_modes():
            text_modes = self._equipment_info["@MODE"]["constraints"]["enumText"]
            count = 0
            for text_mode in text_modes:
                candidate_mode = WaterHeaterOperationMode.by_string(text_mode)
                if new_mode == candidate_mode:
                    payload["@MODE"] = count
                elif candidate_mode == WaterHeaterOperationMode.ELECTRIC_GAS:
                    if new_mode == WaterHeaterOperationMode.ELECTRIC_MODE:
                        payload["@MODE"] = count
                    elif new_mode == WaterHeaterOperationMode.GAS:
                        payload["@MODE"] = count
                count = count + 1

            if not "@MODE" in payload:
                _LOGGER.error("Could not find a matching mode string to set.")

        if payload:
            self._api.publish(payload, self.device_id, self.serial_number)

    def set_set_point(self, set_point: int):
        """Set the equipment set point to set_point."""
        lower, upper = self.set_point_limits
        if lower <= set_point <= upper:
            payload = {"@SETPOINT": set_point}
            self._api.publish(payload, self.device_id, self.serial_number)
        else:
            _LOGGER.error(
                "Set point out of range. Lower: %s Upper: %s Set point: %s",
                lower,
                upper,
                set_point,
            )
