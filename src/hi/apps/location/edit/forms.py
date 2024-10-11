from django import forms


class LocationForm(forms.Form):

    name = forms.CharField()

    svg_file = forms.FileField( label = 'Select an SVG file' )


class LocationViewForm(forms.Form):

    name = forms.CharField()
