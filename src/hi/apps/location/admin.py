from django.contrib import admin

from . import models


class LocationViewInLine(admin.TabularInline):
    model = models.LocationView
    extra = 0
    show_change_link = True

    
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

    inlines = [ LocationViewInLine, ]

    
@admin.register(models.LocationView)
class LocationViewAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'name',
        'location',
        'svg_view_box_str',
        'svg_rotate',
        'order_id',
        'created_datetime',
        'updated_datetime',
    )
    list_select_related = ( 'location', )

    search_fields = ['name']
    ordering = ( 'order_id', )
