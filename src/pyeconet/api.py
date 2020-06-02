from datetime import datetime
import time
import ssl
import json
from typing import Type, TypeVar, List, Dict, Optional
import logging

from pyeconet.errors import PyeconetError, InvalidCredentialsError, GenericHTTPError, InvalidResponseFormat
from pyeconet.equipments import Equipment, EquipmentType
from pyeconet.equipments.water_heater import WaterHeater
from pyeconet.equipments.thermostat import Thermostat

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError
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

    def __init__(self, email: str, password: str, session: ClientSession, account_id: str = None,
                 user_token: str = None) -> None:
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
        self._session: ClientSession = session

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
        session = ClientSession()
        this_class = cls(email, password, session)
        await this_class._authenticate(
            {"email": email, "password": password}
        )
        return this_class

    def subscribe(self):
        """Subscribe to the MQTT updates"""
        if not self._equipment:
            _LOGGER.error("Equipment list is empty, did you call get_equipment before subscribing?")
            return False

        self._mqtt_client = mqtt.Client(self._get_client_id(), clean_session=True, userdata=None, protocol=mqtt.MQTTv311)
        self._mqtt_client.username_pw_set(self._user_token, password=CLEAR_BLADE_SYSTEM_KEY)
        self._mqtt_client.enable_logger()
        self._mqtt_client.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                                  tls_version=ssl.PROTOCOL_TLS, ciphers=None)
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.connect_async(HOST, 1884, 60)
        self._mqtt_client.loop_start()

    def publish(self, payload: Dict, device_id: str, serial_number: str):
        """Publish payload to the specified topic"""
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        transaction_id = f"ANDROID_{date_time}"
        publish_payload = {"transactionId": transaction_id, "device_name": device_id, "serial_number": serial_number}
        publish_payload.update(payload)
        self._mqtt_client.publish(f"user/{self._account_id}/device/desired", payload=json.dumps(publish_payload))

    def unsubscribe(self) -> None:
        self._mqtt_client.loop_stop(force=True)

    def _get_client_id(self) -> str:
        time_string = str(time.time()).replace(".", "")[:13]
        return f"{self.email}{time_string}_android"

    async def _get_equipment(self) -> None:
        """Get a list of all the equipment for this user"""
        _locations: List = await self._get_location()
        for _location in _locations:
            # They spelled it wrong...
            for _equip in _location.get("equiptments"):
                _equip_obj: Equipment = None
                if Equipment._coerce_type_from_string(_equip.get("device_type")) == EquipmentType.WATER_HEATER:
                    _equip_obj = WaterHeater(_equip, self)
                elif Equipment._coerce_type_from_string(_equip.get("device_type")) == EquipmentType.THERMOSTAT:
                    _equip_obj = Thermostat(_equip, self)
                self._equipment[_equip_obj.device_id] = _equip_obj

    async def get_equipment_by_type(self, equipment_type: List) -> Dict:
        """Get a list of equipment by the equipments EquipmentType"""
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
        _headers = HEADERS
        _headers["ClearBlade-UserToken"] = self._user_token
        use_running_session = self._session and not self._session.closed

        if use_running_session:
            session = self._session
        else:
            session = ClientSession()
        try:
            async with session.post(f"{REST_URL}/code/{CLEAR_BLADE_SYSTEM_KEY}/getLocation", headers=HEADERS) as resp:
                if resp.status == 200:
                    _json = await resp.json()
                    _LOGGER.debug(_json)
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
            await session.close()

    async def get_dynamic_action(self, payload: Dict) -> Dict:
        _headers = HEADERS
        _headers["ClearBlade-UserToken"] = self._user_token
        use_running_session = self._session and not self._session.closed

        if use_running_session:
            session = self._session
        else:
            session = ClientSession()
        try:
            async with session.post(f"{REST_URL}/code/{CLEAR_BLADE_SYSTEM_KEY}/dynamicAction", json=payload,
                                    headers=HEADERS) as resp:
                if resp.status == 200:
                    _json = await resp.json()
                    _LOGGER.debug(_json)
                    if _json.get("success"):
                        return _json
                    else:
                        raise InvalidResponseFormat()
                else:
                    raise GenericHTTPError(resp.status)
        except ClientError as err:
            raise err
        finally:
            await session.close()

    async def _authenticate(self, payload: dict) -> None:
        use_running_session = self._session and not self._session.closed
        if use_running_session:
            session = self._session
        else:
            session = ClientSession()
        async with session.post(f"{REST_URL}/user/auth", json=payload, headers=HEADERS) as resp:
            if resp.status == 200:
                _json = await resp.json()
                _LOGGER.debug(_json)
                if _json.get("options")["success"]:
                    self._user_token = _json.get("user_token")
                    self._account_id = _json.get("options").get("account_id")
                else:
                    raise InvalidCredentialsError(_json.get("options")["message"])
            else:
                raise GenericHTTPError(resp.status)

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
            key = _name
            _equipment = self._equipment.get(key)
            if _equipment is not None:
                _equipment._update_equipment_info(unpacked_json)
            else:
                _LOGGER.debug("Received update for non-existent equipment with device name: %s and serial number %s",
                              _name, _serial)
        except Exception as e:
            _LOGGER.exception(e)
            _LOGGER.error("Failed to parse MQTT message: %s", msg.payload)
