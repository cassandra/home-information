from django.db import models

from hi.simulator.profile.models import SimProfile

from .enums import SimEntityType


class DbSimEntity( models.Model ):

    sim_profile = models.ForeignKey(
        SimProfile,
        related_name = 'db_sim_entities',
        verbose_name = 'Simulator Profile',
        on_delete = models.CASCADE,
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
