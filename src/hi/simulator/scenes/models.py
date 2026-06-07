from django.db import models

from hi.simulator.profile.models import SimProfile


class SimScene( models.Model ):
    """A named, reusable demo setup: the per-module profile combination to
    apply, plus an operator-curated subset of state controls to surface on
    the Scenes dashboard. State changes are captured/replayed within a
    scene as SimStateSequence rows.
    """

    name = models.CharField(
        'Scene Name',
        max_length = 64,
        unique = True,
    )
    description = models.TextField(
        'Description',
        null = True, blank = True,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        ordering = [ 'name' ]

    def __str__(self):
        return self.name


class SimSceneBinding( models.Model ):
    """Which SimProfile a given module uses when this scene is applied.
    Modules with no binding are left under individual control ("Off"
    behavior per module).
    """

    scene = models.ForeignKey(
        SimScene,
        verbose_name = 'Scene',
        related_name = 'bindings',
        on_delete = models.CASCADE,
    )
    module_key = models.CharField(
        'Module Key',
        max_length = 96,
    )
    profile = models.ForeignKey(
        SimProfile,
        verbose_name = 'Profile',
        on_delete = models.CASCADE,
    )

    class Meta:
        unique_together = ( 'scene', 'module_key' )
        ordering = [ 'module_key' ]

    def __str__(self):
        return f'{self.scene.name}: [{self.module_key}] -> {self.profile.name}'


class SimSceneControl( models.Model ):
    """An operator-curated state control surfaced on the scene's dashboard.
    Referenced by stable key (module_key / entity_name / sim_state_id) so
    the curated set survives profile re-seeds; resolved to the live
    SimState at render time.
    """

    scene = models.ForeignKey(
        SimScene,
        verbose_name = 'Scene',
        related_name = 'controls',
        on_delete = models.CASCADE,
    )
    module_key = models.CharField(
        'Module Key',
        max_length = 96,
    )
    entity_name = models.CharField(
        'Entity Name',
        max_length = 128,
    )
    sim_state_id = models.CharField(
        'Sim State Id',
        max_length = 128,
    )
    order_id = models.PositiveIntegerField(
        'Order',
        default = 0,
    )

    class Meta:
        unique_together = ( 'scene', 'module_key', 'entity_name', 'sim_state_id' )
        ordering = [ 'order_id', 'module_key', 'entity_name' ]

    def __str__(self):
        return f'{self.scene.name}: [{self.module_key}] {self.entity_name}.{self.sim_state_id}'


class SimStateSequence( models.Model ):
    """A captured, replayable sequence of operator state changes (with
    optional markers) within a scene. Steps reference entities by stable
    key and are stored as a JSON list; played back server-side.
    """

    scene = models.ForeignKey(
        SimScene,
        verbose_name = 'Scene',
        related_name = 'state_sequences',
        on_delete = models.CASCADE,
    )
    name = models.CharField(
        'Name',
        max_length = 128,
    )
    steps_json = models.JSONField(
        'Steps',
        default = list,
    )
    initial_state_json = models.JSONField(
        'Initial State',
        default = list,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now = True,
    )

    class Meta:
        unique_together = ( 'scene', 'name' )
        ordering = [ 'scene', '-updated_datetime' ]

    def __str__(self):
        return f'{self.scene.name}: {self.name}'
