from django import forms

from .models import LocationItemModelMixin, LocationItemPositionModel


class LocationItemPositionForm(forms.Form):

    svg_x = forms.DecimalField(
        label = 'X',
        required = True,
    )
    svg_y = forms.DecimalField(
        label = 'Y',
        required = True,
    )
    svg_scale = forms.DecimalField(
        label = 'Scale',
        required = True,
    )
    svg_rotate = forms.DecimalField(
        label = 'Angle',
        required = True,
    )

    def __init__( self, *args, item_html_id = None, **kwargs ):
        super(LocationItemPositionForm, self).__init__(*args, **kwargs)
        self._item_html_id = item_html_id
        return

    @property
    def item_html_id(self):
        return self._item_html_id
    
    @property
    def content_html_id(self):
        return f'{self.item_html_id}-svg-position'
    
    @classmethod
    def from_models( cls,
                     location_item          : LocationItemModelMixin,
                     location_item_position : LocationItemPositionModel ):
        return cls(
            item_html_id = location_item.html_id,
            initial = {
                'svg_x': location_item_position.svg_x,
                'svg_y': location_item_position.svg_y,
                'svg_scale': location_item_position.svg_scale,
                'svg_rotate': location_item_position.svg_rotate,
            },
        )
         
    def to_location_item_position_model( self, location_item_position_model : LocationItemPositionModel ):
        cleaned_data = self.clean()
        location_item_position_model.svg_x = cleaned_data.get( 'svg_x' )
        location_item_position_model.svg_y = cleaned_data.get( 'svg_y' )
        location_item_position_model.svg_scale = cleaned_data.get( 'svg_scale' )
        location_item_position_model.svg_rotate = cleaned_data.get( 'svg_rotate' )
        return
    
