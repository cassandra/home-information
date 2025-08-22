from django.contrib import admin

from . import models


class LocationViewInLine(admin.TabularInline):
    model = models.LocationView
    extra = 0
    show_change_link = True


class LocationAttributeInLine(admin.TabularInline):
    model = models.LocationAttribute
    extra = 0
    show_change_link = True


class LocationAttributeHistoryInLine(admin.TabularInline):
    model = models.LocationAttributeHistory
    extra = 0
    show_change_link = True
    readonly_fields = ('value', 'changed_datetime')
    can_delete = False

    
@admin.register(models.Location)
class LocationAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'name',
        'svg_fragment_filename',
        'svg_view_box_str',
        'order_id',
        'created_datetime',
        'updated_datetime',
    )

    search_fields = ['name']
    ordering = ( 'order_id', )

    inlines = [ LocationViewInLine, LocationAttributeInLine, ]

    
@admin.register(models.LocationView)
class LocationViewAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'name',
        'location',
        'svg_view_box_str',
        'svg_rotate',
        'order_id',
        'svg_style_name_str',
        'created_datetime',
        'updated_datetime',
    )
    list_select_related = ( 'location', )

    search_fields = ['name']
    ordering = ( 'order_id', )


@admin.register(models.LocationAttribute)
class LocationAttributeAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'location',
        'name',
        'value',
        'value_type_str',
        'attribute_type_str',
        'created_datetime',
    )

    search_fields = ['name', 'location__name']
    readonly_fields = ('location', 'created_datetime')
    inlines = [LocationAttributeHistoryInLine]
