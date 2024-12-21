from django import forms

from .models import SimProfile


class SimProfileForm( forms.ModelForm ):
    
    class Meta:
        model = SimProfile
        fields = (
            'name',
        )
