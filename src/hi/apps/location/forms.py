from decimal import Decimal

from django import forms

from .models import SvgPositionModel


class SvgPositionForm(forms.Form):

    svg_x = forms.DecimalField(
        label = 'X',
        decimal_places = 3,
        required = True,
    )
    svg_y = forms.DecimalField(
        label = 'Y',
        decimal_places = 3,
        required = True,
    )
    svg_scale = forms.DecimalField(
        label = 'Scale',
        decimal_places = 3,
        required = True,
    )
    svg_rotate = forms.DecimalField(
        label = 'Angle',
        decimal_places = 3,
        required = True,
    )
 
    @classmethod
    def from_svg_position_model( cls, svg_position_model : SvgPositionModel ):
        if svg_position_model:
            return cls(
                initial = {
                    'svg_x': svg_position_model.svg_x,
                    'svg_y': svg_position_model.svg_y,
                    'svg_scale': svg_position_model.svg_scale,
                    'svg_rotate': svg_position_model.svg_rotate,
                },
            )
        return cls(
            initial = {
                'svg_scale': Decimal( 1.0 ),
                'svg_rotate': Decimal( 0.0 ),
            },
        )
         
    def to_svg_position_model( self, svg_position_model : SvgPositionModel ):
        svg_position_model.svg_x = self.svg_x
        svg_position_model.svg_y = self.svg_y
        svg_position_model.svg_scale = self.svg_scale
        svg_position_model.svg_rotate = self.svg_rotate
        return
    
