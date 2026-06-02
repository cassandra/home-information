from django import forms

from .models import OpenMeteoSimState


class OpenMeteoSimStateForm( forms.ModelForm ):

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
        model = OpenMeteoSimState
        fields = (
            'temperature_c',
            'temperature_min_c',
            'relative_humidity_pct',
            'dewpoint_c',
            'precipitation_mm',
            'pressure_msl_hpa',
            'windspeed_kmh',
            'winddirection_deg',
            'weathercode',
            'is_day',
        )
        widgets = {
            'temperature_c': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'temperature_min_c': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'relative_humidity_pct': forms.NumberInput( attrs = { 'class': 'form-control' } ),
            'dewpoint_c': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'precipitation_mm': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'pressure_msl_hpa': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'windspeed_kmh': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'winddirection_deg': forms.NumberInput( attrs = { 'class': 'form-control' } ),
            'weathercode': forms.Select( attrs = { 'class': 'custom-select' } ),
        }
        labels = {
            'temperature_c': 'Temperature (°C)',
            'temperature_min_c': 'Daily Low (°C)',
            'relative_humidity_pct': 'Relative Humidity (%)',
            'dewpoint_c': 'Dew Point (°C)',
            'precipitation_mm': 'Precipitation (mm)',
            'pressure_msl_hpa': 'Pressure MSL (hPa)',
            'windspeed_kmh': 'Wind Speed (km/h)',
            'winddirection_deg': 'Wind Direction (°)',
            'weathercode': 'Weather Code',
            'is_day': 'Is Daytime',
        }
