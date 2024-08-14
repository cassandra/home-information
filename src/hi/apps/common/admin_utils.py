from django.urls import reverse
from django.utils.html import format_html


def admin_change_url(obj):
    app_label = obj._meta.app_label
    model_name = obj._meta.model.__name__.lower()
    return reverse('admin:{}_{}_change'.format(
        app_label, model_name
    ), args=(obj.pk,))


def admin_link( model_attribute_name : str,
                short_description : str,
                empty_description : str = "-" ):
    """ Decorator for linking between related fields in admin interfaces. """
    
    def wrap(func):
        def field_func(self, obj):
            related_obj = getattr( obj, model_attribute_name )
            if related_obj is None:
                return empty_description
            url = admin_change_url(related_obj)
            return format_html(
                '<a href="{}">{}</a>',
                url,
                func(self, related_obj)
            )
        field_func.short_description = short_description
        field_func.allow_tags = True
        return field_func
    return wrap
