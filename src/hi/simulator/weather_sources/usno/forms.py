from django import forms

from .models import UsnoSimState


class UsnoSimStateForm( forms.ModelForm ):

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
        model = UsnoSimState
        fields = (
            'sunrise',
            'sunset',
            'solar_noon',
            'moonrise',
            'moonset',
            'fracillum_percent',
            'curphase_str',
            'tz_offset_hours',
        )
        widgets = {
            'sunrise': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'sunset': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'solar_noon': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'moonrise': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'moonset': forms.TextInput( attrs = { 'class': 'form-control', 'placeholder': 'HH:MM' } ),
            'fracillum_percent': forms.NumberInput( attrs = { 'class': 'form-control' } ),
            'curphase_str': forms.Select( attrs = { 'class': 'custom-select' } ),
            'tz_offset_hours': forms.NumberInput( attrs = { 'class': 'form-control' } ),
        }
        labels = {
            'sunrise': 'Sunrise',
            'sunset': 'Sunset',
            'solar_noon': 'Solar Noon',
            'moonrise': 'Moonrise',
            'moonset': 'Moonset',
            'fracillum_percent': 'Moon Illumination (%)',
            'curphase_str': 'Moon Phase',
            'tz_offset_hours': 'TZ Offset (cosmetic)',
        }
