from django.contrib import admin

from . import models


class IntegrationAttributeInLine(admin.TabularInline):
    model = models.IntegrationAttribute
    extra = 0
    show_change_link = True


class IntegrationAttributeHistoryInLine(admin.TabularInline):
    model = models.IntegrationAttributeHistory
    extra = 0
    show_change_link = True
    readonly_fields = ('value', 'changed_datetime')
    can_delete = False


@admin.register(models.Integration)
class IntegrationAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'integration_id',
        'is_enabled',
        'created_datetime',
        'updated_datetime',
    )

    inlines = [ IntegrationAttributeInLine, ]


@admin.register(models.IntegrationAttribute)
class IntegrationAttributeAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'integration',
        'name',
        'value',
        'value_type_str',
        'attribute_type_str',
        'created_datetime',
    )

    search_fields = ['name', 'integration__integration_id']
    readonly_fields = ('integration', 'created_datetime')
    inlines = [IntegrationAttributeHistoryInLine]
