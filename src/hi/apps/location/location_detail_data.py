from dataclasses import dataclass

from .models import Location, LocationView


@dataclass
class LocationDetailData:

    location       : Location
    location_view  : LocationView
