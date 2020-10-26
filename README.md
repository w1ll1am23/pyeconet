# pyeconet
Python3 interface to the unofficial EcoNet API.

**NOTE** This isn't using an official EcoNet API therefore this library could stop working at any time, without warning.

```python
import asyncio
import logging
import time
import getpass

from pyeconet import EcoNetApiInterface
from pyeconet.equipment import EquipmentType
from pyeconet.equipment.water_heater import WaterHeaterOperationMode

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


async def main():
    email = input("Enter your email: ").strip()
    password = "" #getpass.getpass(prompt='Enter your password: ')
    api = await EcoNetApiInterface.login(email, password=password)
    all_equipment = await api.get_equipment_by_type([EquipmentType.WATER_HEATER, EquipmentType.THERMOSTAT])
    #api.subscribe()
    #await asyncio.sleep(5)
    for equip_list in all_equipment.values():
        for equipment in equip_list:
            print(f"Name: {equipment.device_name}")
    #        print(f"Set point: {equipment.set_point}")
    #        print(f"Supports modes: {equipment._supports_modes()}")
    #        print(f"Operation modes: {equipment.modes}")
    #        print(f"Operation mode: {equipment.mode}")
            #await equipment._get_energy_usage()
            #equipment.set_set_point(equipment.set_point + 1)
            #equipment.set_mode(OperationMode.ELECTRIC_MODE)
    #await asyncio.sleep(300000)
    #api.unsubscribe()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```