from django.contrib import admin

from . import models


@admin.register(models.DatabaseLock)
class LocationAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'name',
        'acquired_at',
    )
