from django import forms

from .models import SunriseSunsetSimState


class SunriseSunsetSimStateForm( forms.ModelForm ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        # Each control auto-submits on change (edits take effect
        # immediately in-page) and uses the compact -sm sizing so the
        # label / input / description fit on one row.
        for field in self.fields.values():
            widget = field.widget
            widget.attrs['onchange-async'] = 'true'
            css = widget.attrs.get( 'class', '' )
            if isinstance( widget, forms.Select ):
                widget.attrs['class'] = f'{css} custom-select-sm'.strip()
            elif not isinstance( widget, forms.CheckboxInput ):
                widget.attrs['class'] = f'{css} form-control-sm'.strip()

    class Meta:
        model = SunriseSunsetSimState
        fields = (
            'sunrise',
            'sunset',
            'solar_noon',
            'utc_offset_hours',
            'status_str',
        )
        widgets = {
            'sunrise': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'sunset': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'solar_noon': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'utc_offset_hours': forms.NumberInput( attrs = { 'class': 'form-control' } ),
            'status_str': forms.Select( attrs = { 'class': 'custom-select' } ),
        }
        labels = {
            'sunrise': 'Sunrise',
            'sunset': 'Sunset',
            'solar_noon': 'Solar Noon',
            'utc_offset_hours': 'Console UTC Offset (hours)',
            'status_str': 'API Status',
        }
