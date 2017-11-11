import logging
import json

import requests

from pyeconet.equipment.water_heater import EcoNetWaterHeater
from pyeconet.vacation import EcoNetVacation

BASE_URL = "https://econet-api.rheemcert.com"
LOCATIONS_URL = BASE_URL + "/locations"
DEVICE_URL = BASE_URL + "/equipment/%s"
MODES_URL = DEVICE_URL + "/modes"
USAGE_URL = DEVICE_URL + "/usage"
VACATIONS_URL = BASE_URL + "/vacations"
HEADERS = {"Authorization": "Bearer %s", "Content-Type": "application/json"}
BASIC_HEADERS = {"Authorization": "Basic Y29tLnJoZWVtLmVjb25ldF9hcGk6c3RhYmxla2VybmVs"}
USERNAME = None
PASSWORD = None

_LOGGER = logging.getLogger(__name__)


class EcoNetApiInterface(object):
    """
    API interface object.
    """

    def __init__(self, email, password):
        """
        Create the EcoNet API interface object.
        Args:
            email (str): EcoNet account email address.
            password (str): EcoNet account password.
        """
        self.email = email
        self.password = password
        self.token = None
        self.refresh_token = None
        self.last_api_call = None
        self.state = []
        # get a token
        self.authenticated = self._authenticate()

    @staticmethod
    def set_state(_id, body):
        """
        Set a devices state.
        """
        url = DEVICE_URL % _id
        arequest = requests.put(url, headers=HEADERS, data=json.dumps(body))
        status_code = str(arequest.status_code)
        if status_code != '202':
            _LOGGER.error("State not accepted. " + status_code)
            return False

    @staticmethod
    def get_modes(_id):
        """
        Pull a water heater's modes from the API.
        """
        url = MODES_URL % _id
        arequest = requests.get(url, headers=HEADERS)
        status_code = str(arequest.status_code)
        if status_code == '401':
            _LOGGER.error("Token expired.")
            return False
        return arequest.json()

    @staticmethod
    def get_usage(_id):
        """
        Pull a water heater's usage report from the API.
        """
        url = USAGE_URL % _id
        arequest = requests.get(url, headers=HEADERS)
        status_code = str(arequest.status_code)
        if status_code == '401':
            _LOGGER.error("Token expired.")
            return False
        return arequest.json()

    @staticmethod
    def get_device(_id):
        """
        Pull a device from the API.
        """
        url = DEVICE_URL % _id
        arequest = requests.get(url, headers=HEADERS)
        status_code = str(arequest.status_code)
        if status_code == '401':
            _LOGGER.error("Token expired.")
            return False
        return arequest.json()

    @staticmethod
    def get_locations():
        """
        Pull the accounts locations.
        """
        arequest = requests.get(LOCATIONS_URL, headers=HEADERS)
        status_code = str(arequest.status_code)
        if status_code == '401':
            _LOGGER.error("Token expired.")
            return False
        return arequest.json()

    @staticmethod
    def get_vacations():
        """
        Pull the accounts vacations.
        """
        arequest = requests.get(VACATIONS_URL, headers=HEADERS)
        status_code = str(arequest.status_code)
        if status_code == '401':
            _LOGGER.error("Token expired.")
            return False
        return arequest.json()

    @staticmethod
    def create_vacation(body):
        """
        Create a vacation.
        """
        arequest = requests.post(VACATIONS_URL, headers=HEADERS, data=json.dumps(body))
        status_code = str(arequest.status_code)
        if status_code != '200':
            _LOGGER.error("Failed to create vacation. " + status_code)
            _LOGGER.error(arequest.json())
            return False
        return arequest.json()

    @staticmethod
    def delete_vacation(_id):
        """
        Delete a vacation by ID.
        """
        arequest = requests.delete(VACATIONS_URL + "/" + _id, headers=HEADERS)
        status_code = str(arequest.status_code)
        if status_code != '202':
            _LOGGER.error("Failed to delete vacation. " + status_code)
            return False
        return True

    def _authenticate(self):
        """
        Authenticate with the API and return an authentication token.
        """
        auth_url = BASE_URL + "/auth/token"
        payload = {'username': self.email, 'password': self.password, 'grant_type': 'password'}
        arequest = requests.post(auth_url, data=payload, headers=BASIC_HEADERS)
        status = arequest.status_code
        if status != 200:
            _LOGGER.error("Authentication request failed, please check credintials. " + str(status))
            return False
        response = arequest.json()
        _LOGGER.debug(str(response))
        self.token = response.get("access_token")
        self.refresh_token = response.get("refresh_token")
        _auth = HEADERS.get("Authorization")
        _auth = _auth % self.token
        HEADERS["Authorization"] = _auth
        _LOGGER.info("Authentication was successful, token set.")
        return True


# pylint: disable=too-few-public-methods
class PyEcoNet(object):
    """
    Object used to interact with this library.
    """

    def __init__(self, username, password):
        self.api_interface = EcoNetApiInterface(username, password)
        self.connected = self.api_interface.authenticated
        self.locations = self.api_interface.get_locations()

    def get_water_heaters(self):
        """
        Return a list of water heater devices.

        Parses the response from the locations endpoint in to a pyeconet.WaterHeater.
        """
        water_heaters = []
        for location in self.locations:
            _location_id = location.get("id")
            for device in location.get("equipment"):
                if device.get("type") == "Water Heater":
                    water_heater_modes = self.api_interface.get_modes(device.get("id"))
                    water_heater_usage = self.api_interface.get_usage(device.get("id"))
                    water_heater = self.api_interface.get_device(device.get("id"))
                    vacations = self.api_interface.get_vacations()
                    device_vacations = []
                    for vacation in vacations:
                        for equipment in vacation.get("participatingEquipment"):
                            if equipment.get("id") == water_heater.get("id"):
                                device_vacations.append(EcoNetVacation(vacation, self.api_interface))
                    water_heaters.append(EcoNetWaterHeater(water_heater, water_heater_modes, water_heater_usage,
                                                           _location_id,
                                                           device_vacations,
                                                           self.api_interface))
        return water_heaters
