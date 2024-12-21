from django.db import models
from django.utils.timezone import now

from hi.apps.entity.enums import EntityType


class SimProfile(models.Model):

    name = models.CharField(
        'Name',
        max_length = 128,
        null = False, blank = False,
        unique = True,
    )
    last_switched_to_datetime = models.DateTimeField(
        'Last Switched To',
        default = now,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
    )
    
    class Meta:
        verbose_name = 'Simulator Profile'
        verbose_name_plural = 'Simulator Profiles'
        ordering = [ '-last_switched_to_datetime' ]

        
class DbSimEntity(models.Model):

    sim_profile = models.ForeignKey(
        SimProfile,
        related_name = 'db_sim_entities',
        verbose_name = 'Simulator Profile',
        on_delete = models.CASCADE,
    )
    simulator_id = models.CharField(
        'Simulator Id',
        max_length = 64,
        null = False, blank = False,
    )
    entity_class_name = models.CharField(
        'Entity Class Name',
        max_length = 255,
        null = False, blank = False,
    )
    name = models.CharField(
        'Name',
        max_length = 255,
        null = False, blank = False,
    )
    entity_type_str = models.CharField(
        'Entity Type',
        max_length = 32,
        null = False, blank = False,
    )    
    extra_fields = models.JSONField(
        'Extra Fields',
        default = dict,
        null = False, blank = False,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now=True,
        blank = True,
    )
    
    class Meta:
        verbose_name = 'Simulator Entity'
        verbose_name_plural = 'Simulator Entities'

    @property
    def entity_type(self) -> EntityType:
        return EntityType.from_name_safe( self.entity_type_str )

    @entity_type.setter
    def entity_type( self, entity_type : EntityType ):
        self.entity_type_str = str(entity_type)
        return
