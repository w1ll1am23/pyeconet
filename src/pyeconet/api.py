import time
import ssl
import json
from typing import Type, TypeVar
import logging

from pyeconet.errors import PyeconetError, InvalidCredentialsError, GenericHTTPError

import requests
import paho.mqtt.client as mqtt


HOST = "rheem.clearblade.com"
REST_URL = f"https://{HOST}/api/v/1"
CLEAR_BLADE_SYSTEM_KEY = "e2e699cb0bb0bbb88fc8858cb5a401"
CLEAR_BLADE_SYSTEM_SECRET = "E2E699CB0BE6C6FADDB1B0BC9A20"
HEADERS = {"ClearBlade-SystemKey": CLEAR_BLADE_SYSTEM_KEY, "ClearBlade-SystemSecret": CLEAR_BLADE_SYSTEM_SECRET,
           "Content-Type": "application/json; charset=UTF-8"}

_LOGGER = logging.getLogger(__name__)

ApiType = TypeVar("ApiType", bound="EcoNetApiInterface")


class EcoNetApiInterface:
    """
    API interface object.
    """

    def __init__(self, email: str, password: str, account_id: str = None, user_token: str = None) -> None:
        """
        Create the EcoNet API interface object.
        Args:
            email (str): EcoNet account email address.
            password (str): EcoNet account password.

        """
        self.email: str = email
        self.password: str = password
        self._user_token: str = user_token
        self._account_id: str = account_id

    @property
    def user_token(self) -> str:
        """Return the current user token"""
        return self._user_token

    @property
    def account_id(self) -> str:
        """Return the current user token"""
        return self._account_id

    @classmethod
    async def login(cls: Type[ApiType],
                    email: str,
                    password: str) -> ApiType:
        """Create an EcoNetApiInterface object using email and password
        Args:
            email (str): EcoNet account email address.
            password (str): EcoNet account password.

        """
        this_class = cls(email, password)
        await this_class._authenticate(
            {"email": email, "password": password}
        )
        return this_class

    async def _authenticate(self, payload: dict) -> None:
        auth_response = requests.post(f"{REST_URL}/user/auth", data=json.dumps(payload), headers=HEADERS)
        if auth_response.status_code == 200:
            _json = auth_response.json()
            _LOGGER.debug(_json)
            if _json.get("options")["success"]:
                self._user_token = _json.get("user_token")
                self._account_id = _json.get("options").get("account_id")
            else:
                raise InvalidCredentialsError(_json.get("options")["message"])
        else:
            raise GenericHTTPError(auth_response.status_code)
