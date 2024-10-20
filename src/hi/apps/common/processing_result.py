from dataclasses import dataclass, field
from typing import List


@dataclass
class ProcessingResult:
    """ 
    Generic class for use in reporting the outcome of processing. 
    Has two companion templates for rendering:

        common/panes/processing_result.html
        common/modals/processing_result.html

    Provide this as 'processing_result' in the template context.
    """
    title         : str
    message_list  : List[ str ]     = field( default_factory = list )
    error_list    : List[ str ]     = field( default_factory = list )
