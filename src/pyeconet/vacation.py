import logging

from datetime import timezone
import dateutil.parser
from tzlocal import get_localzone


_LOGGER = logging.getLogger(__name__)


class EcoNetVacation(object):
    """
    Represents an EcoNet vacation.
    """

    def __init__(self, vacation_as_json, api_interface):
        self.api_interface = api_interface
        self.vacation_json = vacation_as_json

    @property
    def id(self):
        return self.vacation_json.get("id")

    @property
    def start_date(self):
        date_string = self.vacation_json.get("startDate")
        utc_date = dateutil.parser.parse(date_string)
        local_tz = get_localzone()
        return utc_date.replace(tzinfo=timezone.utc).astimezone(local_tz)

    @property
    def end_date(self):
        date_string = self.vacation_json.get("endDate")
        utc_date = dateutil.parser.parse(date_string)
        local_tz = get_localzone()
        return utc_date.replace(tzinfo=timezone.utc).astimezone(local_tz)

    @property
    def location_id(self):
        return self.vacation_json["location"]["id"]

    @property
    def equipment_ids(self):
        _ids = []
        equipment_ids = self.vacation_json["participatingEquipment"]
        for equipment_id in equipment_ids:
            _ids.append(equipment_id.get("id"))
        return _ids

    def delete(self):
        self.api_interface.delete_vacation(str(self.id))
