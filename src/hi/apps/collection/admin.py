from django.contrib import admin

from . import models


class CollectionEntityInLine(admin.TabularInline):
    model = models.CollectionEntity
    extra = 0
    show_change_link = True


class CollectionViewInLine(admin.TabularInline):
    model = models.CollectionView
    extra = 0
    show_change_link = True


class CollectionPositionInLine(admin.TabularInline):
    model = models.CollectionPosition
    extra = 0
    show_change_link = True


@admin.register(models.Collection)
class CollectionAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'collection_type_str',
        'created_datetime',
    )
    search_fields = ('name',)
    ordering = ('name',)

    inlines = [
        CollectionEntityInLine,
        CollectionViewInLine,
        CollectionPositionInLine,
    ]
