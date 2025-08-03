from dataclasses import dataclass, field
from typing import Dict

from .transient_models import (
    DataPoint,
    DataPointSource,
    TimeInterval,
)


@dataclass
class IntervalDataPoints:
    """Maps time intervals to their corresponding data points for a single data source."""
    data_interval_map: Dict[TimeInterval, DataPoint] = field(default_factory=dict)
    
    def __getitem__(self, key: TimeInterval) -> DataPoint:
        return self.data_interval_map[key]
    
    def __setitem__(self, key: TimeInterval, value: DataPoint):
        self.data_interval_map[key] = value
    
    def __contains__(self, key: TimeInterval) -> bool:
        return key in self.data_interval_map
    
    def __len__(self) -> int:
        return len(self.data_interval_map)
    
    def __iter__(self):
        return iter(self.data_interval_map)
    
    def keys(self):
        return self.data_interval_map.keys()
    
    def values(self):
        return self.data_interval_map.values()
    
    def items(self):
        return self.data_interval_map.items()


@dataclass
class SourceFieldData:
    """Maps data sources to their interval data points for a specific field."""
    source_map: Dict[DataPointSource, IntervalDataPoints] = field(default_factory=dict)
    
    def __getitem__(self, key: DataPointSource) -> IntervalDataPoints:
        if key not in self.source_map:
            self.source_map[key] = IntervalDataPoints()
        return self.source_map[key]
    
    def __setitem__(self, key: DataPointSource, value: IntervalDataPoints):
        self.source_map[key] = value
    
    def __contains__(self, key: DataPointSource) -> bool:
        return key in self.source_map
    
    def keys(self):
        return self.source_map.keys()
    
    def values(self):
        return self.source_map.values()
    
    def items(self):
        return self.source_map.items()