import logging
import json


_LOGGER = logging.getLogger(__name__)


class EcoNetWaterHeater(object):
    """
    Represents an EcoNet water heater.
    This is a combination of three API endpoints.
    /equipment/{ID}
    /equipment/{ID}/modes
    /equipment/{ID}/usage
    """

    def __init__(self, device_as_json, device_modes_as_json, device_usage_json, api_interface):
        self.api_interface = api_interface
        self.json_state = device_as_json
        self._usage = device_usage_json
        self._modes = []
        for mode in device_modes_as_json:
            self._modes.append(mode.get("name"))

    @property
    def name(self):
        return self.json_state.get('name')

    @property
    def id(self):
        return self.json_state.get('id')

    @property
    def set_point(self):
        return self.json_state.get("setPoint")

    @property
    def min_set_point(self):
        return self.json_state.get("minSetPoint")

    @property
    def max_set_point(self):
        return self.json_state.get("maxSetPoint")

    @property
    def is_on_vacation(self):
        return self.json_state.get("isOnVaction")

    @property
    def is_connected(self):
        return self.json_state.get("isConnected")

    @property
    def is_enabled(self):
        return self.json_state.get("isEnabled")

    @property
    def in_use(self):
        return self.json_state.get("inUse")

    @property
    def mode(self):
        return self.json_state.get("mode")

    @property
    def supported_modes(self):
        return self._modes

    @property
    def usage_unit(self):
        return self._usage["energyUsage"]["unit"]

    @property
    def total_usage_for_today(self):
        hours = self._usage["energyUsage"]["hours"]
        total = 0
        for usage in hours.values():
            total += usage
        return total

    def dump_usage_json(self):
        return json.dumps(self._usage, indent=4, sort_keys=True)

    def update_state(self):
        device_state = self.api_interface.get_device(self.id)
        if device_state:
            self.json_state = device_state
        usage = self.api_interface.get_usage(self.id)
        if usage:
            self._usage = usage

    def set_target_set_point(self, temp):
        if self.min_set_point < temp < self.max_set_point:
            self.api_interface.set_state(self.id, {"setPoint": temp})
        else:
            error = "Invalid set point. Must be < %s and > %s" % self.max_set_point, self.min_set_point
            _LOGGER.error(error)

    def set_vacation_mode(self, on_vacation):
        self.api_interface.set_state({"isOnVacation": on_vacation})

    def set_mode(self, mode):
        if mode in self._modes:
            self.api_interface.set_state({"mode": mode})
        else:
            _LOGGER.error("Invalid mode: " + str(mode))
