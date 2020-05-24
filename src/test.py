import asyncio
import logging
import getpass

from pyeconet import EcoNetApiInterface
from pyeconet.equipments import EquipmentType

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


async def main():
    email = input("Enter your email: ").strip()
    password = getpass.getpass(prompt='Enter your password: ')
    api = await EcoNetApiInterface.login(email, password=password)
    all_equipment = await api.get_equipment_by_type([EquipmentType.WATER_HEATER, EquipmentType.THERMOSTAT])
    for equip_list in all_equipment.values():
        for equipment in equip_list:
            print(f"Name: {equipment.device_name}")
            print(f"Set point: {equipment.set_point}")
            print(f"Supports modes: {equipment._supports_modes()}")
            print(f"Operation modes: {equipment.modes}")
            print(f"Operation mode: {equipment.mode}")
            await equipment._get_energy_usage()
    #api.subscribe()
    #api.unsubscribe()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
