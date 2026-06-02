from django import forms

from .models import NwsSimAlert, NwsSimConditions


class NwsSimConditionsForm( forms.ModelForm ):

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
        model = NwsSimConditions
        fields = (
            'text_description',
            'temperature_c',
            'dewpoint_c',
            'relative_humidity_pct',
            'wind_speed_kmh',
            'wind_direction_deg',
            'barometric_pressure_hpa',
            'cloud_amount',
            'precip_probability_pct',
            'is_daytime',
        )
        widgets = {
            'text_description': forms.TextInput( attrs = { 'class': 'form-control' } ),
            'temperature_c': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'dewpoint_c': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'relative_humidity_pct': forms.NumberInput( attrs = { 'class': 'form-control' } ),
            'wind_speed_kmh': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'wind_direction_deg': forms.NumberInput( attrs = { 'class': 'form-control' } ),
            'barometric_pressure_hpa': forms.NumberInput( attrs = { 'class': 'form-control', 'step': 'any' } ),
            'cloud_amount': forms.Select( attrs = { 'class': 'custom-select' } ),
            'precip_probability_pct': forms.NumberInput( attrs = { 'class': 'form-control' } ),
        }
        labels = {
            'text_description': 'Conditions Text',
            'temperature_c': 'Temperature (°C)',
            'dewpoint_c': 'Dew Point (°C)',
            'relative_humidity_pct': 'Relative Humidity (%)',
            'wind_speed_kmh': 'Wind Speed (km/h)',
            'wind_direction_deg': 'Wind Direction (°)',
            'barometric_pressure_hpa': 'Pressure (hPa)',
            'cloud_amount': 'Sky Cover',
            'precip_probability_pct': 'Precip Probability (%)',
            'is_daytime': 'Is Daytime',
        }


class NwsSimAlertForm( forms.ModelForm ):

    class Meta:
        model = NwsSimAlert
        fields = (
            'is_active',
            'event_code',
            'event_name',
            'severity_str',
            'certainty_str',
            'urgency_str',
            'status_str',
            'category_str',
            'headline',
            'description',
            'instruction',
            'area_desc',
            'effective_offset_secs',
            'expires_offset_secs',
        )
        widgets = {
            'event_code': forms.Select( attrs = { 'class': 'custom-select' } ),
            'severity_str': forms.Select( attrs = { 'class': 'custom-select' } ),
            'certainty_str': forms.Select( attrs = { 'class': 'custom-select' } ),
            'urgency_str': forms.Select( attrs = { 'class': 'custom-select' } ),
            'status_str': forms.Select( attrs = { 'class': 'custom-select' } ),
            'category_str': forms.Select( attrs = { 'class': 'custom-select' } ),
            'event_name': forms.TextInput( attrs = { 'class': 'form-control' } ),
            'headline': forms.TextInput( attrs = { 'class': 'form-control' } ),
            'area_desc': forms.TextInput( attrs = { 'class': 'form-control' } ),
            'description': forms.Textarea( attrs = { 'class': 'form-control', 'rows': 3 } ),
            'instruction': forms.Textarea( attrs = { 'class': 'form-control', 'rows': 2 } ),
            'effective_offset_secs': forms.NumberInput( attrs = { 'class': 'form-control' } ),
            'expires_offset_secs': forms.NumberInput( attrs = { 'class': 'form-control' } ),
        }
        labels = {
            'event_code': 'NWS Event Code',
            'event_name': 'Event',
            'severity_str': 'Severity',
            'certainty_str': 'Certainty',
            'urgency_str': 'Urgency',
            'status_str': 'Status',
            'category_str': 'Category',
            'area_desc': 'Affected Areas',
            'effective_offset_secs': 'Effective Offset (sec)',
            'expires_offset_secs': 'Expires Offset (sec)',
        }
