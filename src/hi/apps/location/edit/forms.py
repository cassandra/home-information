from django import forms


class LocationViewForm(forms.Form):

    name = forms.CharField()
