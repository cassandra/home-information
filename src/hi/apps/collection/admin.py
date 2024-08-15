from django.contrib import admin

from .models import Collection, CollectionEntityRelation


class CollectionEntityRelationInline(admin.TabularInline):
    model = CollectionEntityRelation
    extra = 1  # Number of empty forms to display in the inline

    
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    inlines = [ CollectionEntityRelationInline ]
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)
