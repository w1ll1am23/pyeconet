import datetime
import logging


_LOGGER = logging.getLogger(__name__)


class EcoNetWaterHeater(object):

    def __init__(self, device_as_json, device_modes_as_json, api_interface):
        self.api_interface = api_interface
        self.json_state = device_as_json
        self._modes = []
        for mode in device_modes_as_json:
            self._modes.append(mode.get("name"))

    def name(self):
        return self.json_state.get('name')

    def id(self):
        return self.json_state.get('id')

    def set_point(self):
        return self.json_state.get("setPoint")

    def min_set_point(self):
        return self.json_state.get("minSetPoint")

    def max_set_point(self):
        return self.json_state.get("maxSetPoint")

    def is_on_vacation(self):
        return self.json_state.get("isOnVaction")

    def is_connected(self):
        return self.json_state.get("isConnected")

    def is_enabled(self):
        return self.json_state.get("isEnabled")

    def in_use(self):
        return self.json_state.get("inUse")

    def mode(self):
        return self.json_state.get("mode")

    def supported_modes(self):
        return self._modes

    def update_state(self):
        device_state = self.api_interface.get_device(self.id())
        if device_state:
            self.json_state = device_state 

    def set_target_set_point(self, temp):
        if self.min_set_point() < temp < self.max_set_point():
            self.api_interface.set_state(self.id(), {"setPoint": temp})

    def set_vacation_mode(self, on_vacation):
        self.api_interface.set_state({"isOnVacation": on_vacation})

    def set_mode(self, mode):
        if mode in self._modes:
           self.api_interface.set_state({"mode": mode})
        else:
            _LOGGER.error("Invalid mode: " + str(mode)) 
