# pyeconet
Python3 interface to the unofficial EcoNet API.

**NOTE** This isn't using an official EcoNet API therefore this library could stop working at any time, without warning.

```python
import time
from datetime import datetime, timezone
from pyeconet.api import PyEcoNet
from tzlocal import get_localzone

email = "YOUR_EMAIL"
password = "Your Password"
econet = PyEcoNet(email, password)
devices = econet.get_water_heaters()
local_tz = get_localzone()
start = datetime(2017, 12, 20, 1, 0, 0, tzinfo=local_tz)
end = datetime(2017, 12, 21, 1, 0, 0, tzinfo=local_tz)
for water_heater in devices:
    print(str(water_heater.get_vacations()))
    #continue
    water_heater.set_vacation_mode(start, end)
    print(str(water_heater.get_vacations()))
    print(water_heater.name)
    print(water_heater.id)
    print(water_heater.set_point)
    print(water_heater.min_set_point)
    print(water_heater.max_set_point)
    print(water_heater.mode)
    print(str(water_heater.supported_modes))
    print("vacation: " + str(water_heater.is_on_vacation))
    print(water_heater.is_connected)
    print(water_heater.is_enabled)
    print(water_heater.in_use)
    print(water_heater.usage_unit)
    print(water_heater.total_usage_for_today)
    print(water_heater.dump_usage_json())
    water_heater.set_target_set_point(119)
    time.sleep(305)
    water_heater.update_state()
    time.sleep(15)
    print(water_heater.set_point)
```