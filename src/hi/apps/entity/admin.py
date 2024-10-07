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

    
class EntityStateDelegationInLine(admin.TabularInline):
    model = models.EntityStateDelegation
    extra = 0
    show_change_link = True


class EntityViewInLine(admin.TabularInline):
    model = models.EntityView
    extra = 0
    show_change_link = True


@admin.register(models.Entity)
class EntityAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'entity_type_str',
        'integration_type_str',
        'integration_key',
        'created_datetime',
    )

    search_fields = ['name']

    inlines = [
        AttributesInLine,
        StatesInLine,
        EntityViewInLine,
        PositionInLine,
        PathInLine,
        EntityStateDelegationInLine,
    ]
    

@admin.register(models.EntityStateDelegation)
class EntityStateDelegationAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'entity_state',
        'delegate_entity',
        'created_datetime',
    )

    search_fields = ['entity__name']
    readonly_fields = ( 'entity_state', 'delegate_entity', )
    
