import asyncio
import logging

from pyeconet import EcoNetApiInterface

import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.INFO)
requests_log.propagate = True


async def main():
    api = await EcoNetApiInterface.login("EMAIL", "PASSWORD")
    all_equipment = await api.get_equipment()
    for equipment in all_equipment:
        print("Device type: ", str(equipment.type))
        print("Device name id: ", equipment.device_name)
        print("Device tank capacity: ", equipment.tank_hot_water_capacity)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
