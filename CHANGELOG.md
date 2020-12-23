# Change log

## 0.1.9
- Update to water heater tank capacity (new file names)

## 0.1.8
- HVAC humidity updates

## 0.1.7
- Fixed set heat temp defect

## 0.1.5
- Renamed equipments to equipment

## 0.1.4
- Move to the new API and MQTT push update system

## 0.0.12
- Added water usage and usage reports for month and year

## 0.0.11
- Beta release

## 0.0.10
- Actualy did what I said I did in 0.0.9

## 0.0.9
- Fix string formatting for python versions < 3.6

## 0.0.8
- Fix set temp to include upper and lower limit

## 0.0.7
- Fixed exception from energy usage and added more json attributes

## 0.0.6
- Modes are now sent to the modes endpoint not directly to the device endpoint

## 0.0.5
- Switch json.decoder.JSONDecodeError to ValueError

## 0.0.4
- Natural gas water heaters don't support usage. Handle usage errors.

## 0.0.3
- Pull vacations on water heater update

## 0.0.2
- Fixed Vacation typo
- Added device ID to set_state call in set_mode
- Throttled API update calls to 5 minutes

## 0.0.1
- Initial support for EcoNet water heaters.
