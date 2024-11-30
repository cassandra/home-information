from hi.apps.entity.models import EntityPosition
from hi.apps.location.edit.forms import LocationItemPositionForm


class EntityPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = EntityPosition
