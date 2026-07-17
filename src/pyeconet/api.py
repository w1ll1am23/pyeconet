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

import aiohttp
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

# Via https://knowledge.digicert.com/general-information/digicert-trusted-root-authority-certificates
# DigiCert Global Root CA
# Valid until: 10/Nov/2031
# Serial #: 08:3B:E0:56:90:42:46:B1:A1:75:6A:C9:59:91:C7:4A
# SHA1 Fingerprint: A8:98:5D:3A:65:E5:E5:C4:B2:D7:D6:6D:40:C6:DD:2F:B1:9C:54:36
# SHA256 Fingerprint: 43:48:A0:E9:44:4C:78:CB:26:5E:05:8D:5E:89:44:B4:D8:4F:96:62:BD:26:DB:25:7F:89:34:A4:43:C7:01:61
#
# This root certificate was explicitly distrusted by Mozilla. Refer to these articles:
# https://knowledge.digicert.com/general-information/digicert-root-and-intermediate-ca-certificate-updates-2023
# https://wiki.mozilla.org/CA/Root_CA_Lifecycles#2026_Websites_Trust_Bit_Removals
#
# We know that the common Rheem IoT endpoint uses a certificate signed by this root certificate.
# Because some environments rely on the Mozilla CA bundle, when they update to any version of the bundle newer
# than April 15, 2026, they no longer trust the root certificate, and consequently no longer trust the downstream
# certificate used with the endpoint. As a workaround, we can re-add the distrusted root certificate as trusted,
# similar to what the Android application does. This essentially reverts the updated Mozilla CA bundle for this
# one certificate, which solves the problem in those environments, without making those devices any less "secure"
# than they were before. It also keeps the scope of the trust narrowly on the Rheem EcoNet integration instead of
# asking users to change their OS's entire CA configuration.
#
# Ideally the next certificate renewal will use a new root and intermediate that do not have this trust issue.
# If they do, this workaround can be reverted.
CLEAR_BLADE_DIGICERT_DISTRUSTED_ROOT = """-----BEGIN CERTIFICATE-----
MIIDrzCCApegAwIBAgIQCDvgVpBCRrGhdWrJWZHHSjANBgkqhkiG9w0BAQUFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBD
QTAeFw0wNjExMTAwMDAwMDBaFw0zMTExMTAwMDAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IENBMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4jvhEXLeqKTTo1eqUKKPC3eQyaKl7hLOllsB
CSDMAZOnTjC3U/dDxGkAV53ijSLdhwZAAIEJzs4bg7/fzTtxRuLWZscFs3YnFo97
nh6Vfe63SKMI2tavegw5BmV/Sl0fvBf4q77uKNd0f3p4mVmFaG5cIzJLv07A6Fpt
43C/dxC//AH2hdmoRBBYMql1GNXRor5H4idq9Joz+EkIYIvUX7Q6hL+hqkpMfT7P
T19sdl6gSzeRntwi5m3OFBqOasv+zbMUZBfHWymeMr/y7vrTC0LUq7dBMtoM1O/4
gdW7jVg/tRvoSSiicNoxBN33shbyTApOB6jtSj1etX+jkMOvJwIDAQABo2MwYTAO
BgNVHQ8BAf8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUA95QNVbR
TLtm8KPiGxvDl7I90VUwHwYDVR0jBBgwFoAUA95QNVbRTLtm8KPiGxvDl7I90VUw
DQYJKoZIhvcNAQEFBQADggEBAMucN6pIExIK+t1EnE9SsPTfrgT1eXkIoyQY/Esr
hMAtudXH/vTBH1jLuG2cenTnmCmrEbXjcKChzUyImZOMkXDiqw8cvpOp/2PV5Adg
06O/nVsJ8dWO41P0jmP6P6fbtGbfYmbW0W5BjfIttep3Sp+dWOIrWcBAI+0tKIJF
PnlUkiaY4IBIqDfv8NZ5YBberOgOzW6sRBc4L0na4UU+Krk2U886UAb3LujEV0ls
YSEY1QSteDwsOoBrp+uvFRTp2InBuThs4pFsiv9kuXclVzDAGySj4dzp30d8tbQk
CAUw7C29C79Fv1C5qfPrmAESrciIxpg0X40KPMbp1ZWVbd4=
-----END CERTIFICATE-----"""

def _create_ssl_context() -> ssl.SSLContext:
    """Create a SSL context for the MQTT connection."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.load_default_certs()
    context.load_verify_locations(cadata=CLEAR_BLADE_DIGICERT_DISTRUSTED_ROOT)
    context.verify_mode = ssl.CERT_REQUIRED
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

        async with aiohttp.request(
                'POST',
                f"{REST_URL}/code/{CLEAR_BLADE_SYSTEM_KEY}/getUserDataForApp",
                ssl=_SSL_CONTEXT,
                json=payload,
                headers=_headers
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

    async def get_dynamic_action(self, payload: Dict) -> Dict:
        _headers = HEADERS.copy()
        _headers["ClearBlade-UserToken"] = self._user_token

        async with aiohttp.request(
                'POST',
                f"{REST_URL}/code/{CLEAR_BLADE_SYSTEM_KEY}/dynamicAction",
                ssl=_SSL_CONTEXT,
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

    async def _authenticate(self, payload: dict) -> None:

        async with aiohttp.request(
                'POST',
                f"{REST_URL}/user/auth",
                ssl=_SSL_CONTEXT,
                json=payload,
                headers=HEADERS
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
