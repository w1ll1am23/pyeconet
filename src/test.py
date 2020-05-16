import asyncio
import logging
import getpass

from pyeconet import EcoNetApiInterface

import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.INFO)
requests_log.propagate = True


async def main():
    email = getpass.getpass(prompt='Enter your email: ')
    password = getpass.getpass(prompt='Enter your password: ')
    api = await EcoNetApiInterface.login(email, password=password)
    connected = await api.subscribe()
    all_equipment = await api.get_equipment()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
