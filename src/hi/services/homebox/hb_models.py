from typing import Dict, List
from dataclasses import dataclass


class HbApi:
    """ Central place for translating HomeBox API response strings and internal variables. """

    ID_FIELD = 'id'
    NAME_FIELD = 'name'
    DESCRIPTION_FIELD = 'description'
    SERIAL_NUMBER_FIELD = 'serialNumber'
    MODEL_NUMBER_FIELD = 'modelNumber'
    MANUFACTURER_FIELD = 'manufacturer'
    NOTES_FIELD = 'notes'
    ATTACHMENTS_FIELD = 'attachments'
    FIELDS_FIELD = 'fields'


@dataclass
class HbItem:
    """ Wraps the JSON object from the API """

    api_dict: Dict

    @property
    def id(self) -> str:
        return self.api_dict.get(HbApi.ID_FIELD)

    @property
    def name(self) -> str:
        return self.api_dict.get(HbApi.NAME_FIELD, '')

    @property
    def description(self) -> str:
        return self.api_dict.get(HbApi.DESCRIPTION_FIELD, '')

    @property
    def serial_number(self) -> str:
        return self.api_dict.get(HbApi.SERIAL_NUMBER_FIELD, '')

    @property
    def model_number(self) -> str:
        return self.api_dict.get(HbApi.MODEL_NUMBER_FIELD, '')

    @property
    def manufacturer(self) -> str:
        return self.api_dict.get(HbApi.MANUFACTURER_FIELD, '')

    @property
    def notes(self) -> str:
        return self.api_dict.get(HbApi.NOTES_FIELD, '')

    @property
    def attachments(self) -> List[Dict]:
        return self.api_dict.get(HbApi.ATTACHMENTS_FIELD, [])

    @property
    def fields(self) -> List[Dict]:
        return self.api_dict.get(HbApi.FIELDS_FIELD, [])
