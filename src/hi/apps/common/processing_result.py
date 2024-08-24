from dataclasses import dataclass, field
from typing import List


@dataclass
class ProcessingResult:
    """ Generic class for use in reporting the outcome of processing. """
    title         : str
    message_list  : List[ str ]     = field( default_factory = list )
    error_list    : List[ str ]     = field( default_factory = list )
