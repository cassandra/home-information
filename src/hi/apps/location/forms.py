from decimal import Decimal

from django import forms

from .models import SvgPositionModel


class SvgPositionForm(forms.Form):

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
        cleaned_data = self.clean()
        svg_position_model.svg_x = cleaned_data.get( 'svg_x' )
        svg_position_model.svg_y = cleaned_data.get( 'svg_y' )
        svg_position_model.svg_scale = cleaned_data.get( 'svg_scale' )
        svg_position_model.svg_rotate = cleaned_data.get( 'svg_rotate' )
        return
    
