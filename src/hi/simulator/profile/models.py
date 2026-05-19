from django.db import models


class SimProfile( models.Model ):
    """Per-module profile of simulator data. Each module (service
    simulator or weather source) maintains its own profile space —
    e.g., ``module_key = 'hi.simulator.services.hass'`` profiles are
    independent of ``module_key = 'hi.simulator.services.zoneminder'``
    profiles, so an operator can iterate one module's scenario
    without disturbing another's.
    """

    module_key = models.CharField(
        'Module Key',
        max_length = 96,
    )
    name = models.CharField(
        'Profile Name',
        max_length = 64,
    )
    last_switched_to_datetime = models.DateTimeField(
        'Last Switched To',
        null = True,
        blank = True,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        unique_together = ( 'module_key', 'name' )
        ordering = [ 'module_key', 'name' ]

    def __str__(self):
        return f'[{self.module_key}] {self.name}'
