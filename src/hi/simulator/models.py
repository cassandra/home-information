from django.db import models
from django.utils.timezone import now

from .enums import SimEntityType


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

    def __str__(self):
        return f'{self.name} [{self.id}]'

    
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
    entity_fields_class_id = models.CharField(
        'Entity Fields Class Id',
        max_length = 255,
        null = False, blank = False,
    )
    sim_entity_type_str = models.CharField(
        'Entity Type',
        max_length = 32,
        null = False, blank = False,
    )    
    sim_entity_fields_json = models.JSONField(
        'Entity Fields',
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
    def sim_entity_type(self) -> SimEntityType:
        return SimEntityType.from_name_safe( self.sim_entity_type_str )

    @sim_entity_type.setter
    def sim_entity_type( self, sim_entity_type : SimEntityType ):
        self.sim_entity_type_str = str(sim_entity_type)
        return
