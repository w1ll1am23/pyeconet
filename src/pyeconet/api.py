from datetime import datetime
import time
import ssl
import json
from typing import Type, TypeVar, List, Dict, Optional
import logging

from pyeconet.errors import (
    PyeconetError,
    InvalidCredentialsError,
    GenericHTTPError,
    InvalidResponseFormat,
)
from pyeconet.equipment import Equipment, EquipmentType
from pyeconet.equipment.water_heater import WaterHeater
from pyeconet.equipment.thermostat import Thermostat

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError
import paho.mqtt.client as mqtt

HOST = "rheem.clearblade.com"
REST_URL = f"https://{HOST}/api/v/1"
CLEAR_BLADE_SYSTEM_KEY = "e2e699cb0bb0bbb88fc8858cb5a401"
CLEAR_BLADE_SYSTEM_SECRET = "E2E699CB0BE6C6FADDB1B0BC9A20"
HEADERS = {
    "ClearBlade-SystemKey": CLEAR_BLADE_SYSTEM_KEY,
    "ClearBlade-SystemSecret": CLEAR_BLADE_SYSTEM_SECRET,
    "Content-Type": "application/json; charset=UTF-8",
}

_LOGGER = logging.getLogger(__name__)

ApiType = TypeVar("ApiType", bound="EcoNetApiInterface")


def _create_ssl_context() -> ssl.SSLContext:
    """Create a SSL context for the MQTT connection."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.load_default_certs()
    return context


_SSL_CONTEXT = _create_ssl_context()


class EcoNetApiInterface:
    """
    API interface object.
    """

    def __init__(
            self, email: str, password: str, account_id: str = None, user_token: str = None
    ) -> None:
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
        self._locations: List = []
        self._equipment: Dict = {}
        self._mqtt_client = None

    @property
    def user_token(self) -> str:
        """Return the current user token"""
        return self._user_token

    @property
    def account_id(self) -> str:
        """Return the current user token"""
        return self._account_id

    @classmethod
    async def login(cls: Type[ApiType], email: str, password: str) -> ApiType:
        """Create an EcoNetApiInterface object using email and password
        Args:
            email (str): EcoNet account email address.
            password (str): EcoNet account password.

        """
        this_class = cls(email, password)
        await this_class._authenticate({"email": email, "password": password})
        return this_class

    def check_mode_enum(self, equip, enumtext=None):
        # Fix enumeration of Emergency Heat in Thermostat, maybe others?
        if "@MODE" in equip and isinstance(equip["@MODE"], Dict):
            if 'constraints' in equip["@MODE"]:
                enumtext = equip["@MODE"]['constraints']['enumText']
            status = equip["@MODE"].get('status')
            if enumtext and status:
                value = equip["@MODE"]['value']
                try:
                    enumtext_index_by_status = enumtext.index(status)
                    if value != enumtext_index_by_status:
                        _LOGGER.debug("Enum value mismatch: "
                                      f"{enumtext[value]} != "
                                      f"{equip['@MODE']['status']}")
                        equip["@MODE"]['value'] = enumtext_index_by_status
                except ValueError:
                    # friedrich seems to return cool vs cooling which causes this issue but the value (index)
                    # is still right so maybe we can ignore it?
                    _LOGGER.debug("Enum value mismatch: "
                                  f"{enumtext[value]} != "
                                  f"{equip['@MODE']['status']}")

        return equip, enumtext

    def check_update_enum(self, equip, update):
        # Update messages only have the status and value, so get the enumtext
        equip, enumtext = self.check_mode_enum(equip)
        # Fix the update
        update, __ = self.check_mode_enum(update, enumtext)
        return equip, update

    def subscribe(self):
        """Subscribe to the MQTT updates"""
        if not self._equipment:
            _LOGGER.error(
                "Equipment list is empty, did you call get_equipment before subscribing?"
            )
            return False

        self._mqtt_client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=self._get_client_id(),
            clean_session=True,
            userdata=None,
            protocol=mqtt.MQTTv311,
        )
        self._mqtt_client.username_pw_set(
            self._user_token, password=CLEAR_BLADE_SYSTEM_KEY
        )
        self._mqtt_client.enable_logger()

        self._mqtt_client.tls_set_context(_SSL_CONTEXT)
        self._mqtt_client.tls_insecure_set(False)

        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.connect_async(HOST, 1884, 60)
        self._mqtt_client.loop_start()

    def publish(self, payload: Dict, device_id: str, serial_number: str):
        """Publish payload to the specified topic"""
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        transaction_id = f"ANDROID_{date_time}"
        publish_payload = {
            "transactionId": transaction_id,
            "device_name": device_id,
            "serial_number": serial_number,
        }
        publish_payload.update(payload)
        self._mqtt_client.publish(
            f"user/{self._account_id}/device/desired",
            payload=json.dumps(publish_payload),
        )

    def unsubscribe(self) -> None:
        self._mqtt_client.loop_stop()

    def _get_client_id(self) -> str:
        time_string = str(time.time()).replace(".", "")[:13]
        return f"{self.email}{time_string}_android"

    async def _get_equipment(self) -> None:
        """Get a list of all the equipment for this user"""
        _locations: List = await self._get_location()
        for _location in _locations:
            # They spelled it wrong...
            for _equip in _location.get("equiptments"):
                # Early exit if server returned error code
                if "error" in _equip:
                    _LOGGER.debug("EcoNet equipment error message"
                                  f": {_equip.get('error')}")
                    continue
                _equip, __ = self.check_mode_enum(_equip)
                _equip_obj: Equipment = None
                if (
                        Equipment._coerce_type_from_string(_equip.get("device_type"))
                        == EquipmentType.WATER_HEATER
                ):
                    _equip_obj = WaterHeater(_equip, self)
                    self._equipment[_equip_obj.serial_number] = _equip_obj
                elif (
                        Equipment._coerce_type_from_string(_equip.get("device_type"))
                        == EquipmentType.THERMOSTAT
                ):
                    _equip_obj = Thermostat(_equip, self)
                    self._equipment[_equip_obj.serial_number] = _equip_obj
                    for zoning_device in _equip.get("zoning_devices", []):
                        _equip_obj = Thermostat(zoning_device, self)
                        self._equipment[_equip_obj.serial_number] = _equip_obj

    async def refresh_equipment(self) -> None:
        """Get a list of all the equipment for this user"""
        _locations: List = await self._get_location()
        for _location in _locations:
            # They spelled it wrong...
            for _equip in _location.get("equiptments"):
                serial = _equip.get("serial_number")
                equipment = self._equipment.get(serial)
                if equipment:
                    _equip, __ = self.check_mode_enum(_equip)
                    equipment.update_equipment_info(_equip)

    async def get_equipment_by_type(self, equipment_type: List) -> Dict:
        """Get a list of equipment by the equipment EquipmentType"""
        if not self._equipment:
            await self._get_equipment()
        _equipment = {}
        for _equip_type in equipment_type:
            _equipment[_equip_type] = []
        for value in self._equipment.values():
            if value.type in equipment_type:
                _equipment[value.type].append(value)
        return _equipment

    async def _get_location(self) -> List[Dict]:
        _headers = HEADERS.copy()
        _headers["ClearBlade-UserToken"] = self._user_token
        payload = {"resource": "friedrich"}
        # payload = {"location_only": False, "type": "com.econet.econetconsumerandroid", "version": "6.0.0-375-01b4870e"}

        _session = ClientSession()
        try:
            async with _session.post(
                    f"{REST_URL}/code/{CLEAR_BLADE_SYSTEM_KEY}/getUserDataForApp", json=payload, headers=_headers
            ) as resp:
                if resp.status == 200:
                    _json = await resp.json()
                    _LOGGER.debug(json.dumps(_json, indent=2))
                    if _json.get("success"):
                        self._locations = _json["results"]["locations"]
                        return self._locations
                    else:
                        raise InvalidResponseFormat()
                else:
                    raise GenericHTTPError(resp.status)
        except ClientError as err:
            raise err
        finally:
            await _session.close()

    async def get_dynamic_action(self, payload: Dict) -> Dict:
        _headers = HEADERS.copy()
        _headers["ClearBlade-UserToken"] = self._user_token

        _session = ClientSession()
        try:
            async with _session.post(
                    f"{REST_URL}/code/{CLEAR_BLADE_SYSTEM_KEY}/dynamicAction",
                    json=payload,
                    headers=_headers,
            ) as resp:
                if resp.status == 200:
                    _json = await resp.json()
                    _LOGGER.debug(json.dumps(_json, indent=2))
                    if _json.get("success"):
                        return _json

                    raise InvalidResponseFormat()

                raise GenericHTTPError(resp.status)
        except ClientError as err:
            raise err
        finally:
            await _session.close()

    async def _authenticate(self, payload: dict) -> None:

        _session = ClientSession()
        try:
            async with _session.post(
                    f"{REST_URL}/user/auth", json=payload, headers=HEADERS
            ) as resp:
                if resp.status == 200:
                    _json = await resp.json()
                    _LOGGER.debug(json.dumps(_json, indent=2))
                    if _json.get("options")["success"]:
                        self._user_token = _json.get("user_token")
                        self._account_id = _json.get("options").get("account_id")
                    else:
                        raise InvalidCredentialsError(_json.get("options")["message"])
                else:
                    raise GenericHTTPError(resp.status)
        finally:
            await _session.close()

    def _on_connect(self, client, userdata, flags, rc):
        _LOGGER.debug(f"Connected with result code: {str(rc)}")
        client.subscribe(f"user/{self._account_id}/device/reported")
        client.subscribe(f"user/{self._account_id}/device/desired")

    def _on_disconnect(self, client, userdata, rc):
        _LOGGER.debug(f"Disconnected with result code: {str(rc)}")
        if rc != 0:
            _LOGGER.error("EcoNet MQTT unexpected disconnect. Attempting to reconnect.")
            client.reconnect()

    def _on_message(self, client, userdata, msg):
        """When a MQTT message comes in push that update to the specified equipment"""
        try:
            unpacked_json = json.loads(msg.payload)
            _LOGGER.debug("MQTT message from topic: %s", msg.topic)
            _LOGGER.debug(json.dumps(unpacked_json, indent=2))
            _name = unpacked_json.get("device_name")
            _serial = unpacked_json.get("serial_number")
            key = _serial
            _equipment = self._equipment.get(key)
            if _equipment is not None:
                _equipment._equipment_info, unpacked_json = self.check_update_enum(_equipment._equipment_info,
                                                                                   unpacked_json)
                _equipment.update_equipment_info(unpacked_json)
            # Nasty hack to push signal updates to the device it belongs to
            elif "@SIGNAL" in str(unpacked_json):
                for _equipment in self._equipment.values():
                    if _equipment.device_id == _name:
                        # Don't break after update for multi zone HVAC systems
                        _equipment.update_equipment_info(unpacked_json)
            else:
                _LOGGER.debug(
                    "Received update for non-existent equipment with device name: %s and serial number %s",
                    _name,
                    _serial,
                )
        except Exception as e:
            _LOGGER.exception(e)
            _LOGGER.error("Failed to parse the following MQTT message: %s", msg.payload)
