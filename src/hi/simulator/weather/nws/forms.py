from django import forms

from .models import NwsSimAlert


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
