from typing import Sequence

from django.db import models
from django.db.models import Q

from .integration_key import IntegrationKey


class IntegrationKeyManager(models.Manager):

    def filter_by_integration_key( self, integration_key : IntegrationKey ):
        return self.filter( integration_id = integration_key.integration_id,
                            integration_name = integration_key.integration_name )

    def filter_by_integration_keys( self, integration_keys : Sequence[ IntegrationKey ] ):
        query = Q()
        for integration_key in integration_keys:
            query |= Q( integration_id = integration_key.integration_id,
                        integration_name = integration_key.integration_name )
            continue
        return self.filter(query)
    
