from dataclasses import dataclass
from typing import List

from hi.apps.entity.models import Entity

from .models import Collection


@dataclass
class CollectionData:

    collection             : Collection
    entity_list            : List[ Entity ]
