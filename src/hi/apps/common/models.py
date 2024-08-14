from dataclasses import dataclass, field
import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class Histogram:
    label             : str                        = 'Untitled'
    category_label    : str                        = 'Value'
    count_label       : str                        = 'Count'
    total_sum         : int                        = 0
    sort_by_value     : bool                       = True
    sort_disabled     : bool                       = False
    histogram         : Dict[ object, int ]        = field( default_factory = dict )
    limit             : int                        = 0

    def __str__(self):
        return '%s: %s' % ( self.label,
                            json.dumps( self._stats.histogram, indent=4, sort_keys=True  ))
     
    def get( self, category, default = 0 ):
        return self.histogram.get( category, default )

    @property
    def total_unique(self):
        return len(self.histogram)
    
    def increment( self, category, value = 1 ):
        self.total_sum += value
        if category not in self.histogram:
            self.histogram[category] = 0
        self.histogram[category] += value
        return

    def items( self ):
        item_list = [ ( x, y ) for x, y in self.histogram.items() ]

        # If no sorting, use insertion ordering
        if not self.sort_disabled:        
            if self.sort_by_value:
                item_list.sort( key = lambda item: item[1], reverse = True )
            else:
                item_list.sort( key = lambda item: item[0], reverse = True )
            
        for idx, item in enumerate( item_list ):
            if self.limit and idx >= self.limit:
                return
            if self.total_sum > 0:
                percentage = 100.0 * item[1] / self.total_sum
            else:
                percentage = 0.0
            yield ( item[1], item[0], percentage )
            continue
        return

    def update( self, histogram ):
        for category, count in histogram.histogram.items():
            self.increment( category, value = count )
            continue
        return
    
    def to_django_choices(self):
        choices = list()
        for value, category, _ in self.items():
            choices.append( ( category, f'{category} ({value})' ) )
            continue
        return choices

