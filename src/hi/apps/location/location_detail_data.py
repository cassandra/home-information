from dataclasses import dataclass

from .models import Location


@dataclass
class LocationDetailData:

    location             : Location
