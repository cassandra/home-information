from django.contrib import admin

from . import models


class AttributesInLine(admin.TabularInline):
    model = models.Attribute
    extra = 0
    show_change_link = True

    
class StatesInLine(admin.TabularInline):
    model = models.EntityState
    extra = 0
    show_change_link = True

    
class PositionInLine(admin.TabularInline):
    model = models.EntityPosition
    extra = 0
    show_change_link = True

    
class PathInLine(admin.TabularInline):
    model = models.EntityPath
    extra = 0
    show_change_link = True


@admin.register(models.Entity)
class EntityAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'entity_type_str',
        'created_datetime',
    )

    search_fields = ['name']

    inlines = [ AttributesInLine, StatesInLine, PositionInLine, PathInLine ]
    
