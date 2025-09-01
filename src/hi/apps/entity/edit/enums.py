from hi.apps.common.enums import LabeledEnum


class EntityTransitionType(LabeledEnum):
    """Types of entity type transitions that can occur during entity type changes."""
    
    # Successful transition types
    ICON_TO_ICON = ('Icon to Icon', 'Transition between two icon-based entity types')
    ICON_TO_PATH = ('Icon to Path', 'Transition from icon-based to path-based entity type')  
    PATH_TO_ICON = ('Path to Icon', 'Transition from path-based to icon-based entity type')
    PATH_TO_PATH = ('Path to Path', 'Transition between two path-based entity types')
    CREATED_POSITION = ('Created Position', 'Created new entity position for entity without existing representation')
    CREATED_PATH = ('Created Path', 'Created new entity path for entity without existing representation')
    
    # Error/edge case types  
    NO_LOCATION_VIEW = ('No Location View', 'No location view provided for transition')
    NO_TRANSITION_NEEDED = ('No Transition Needed', 'Entity type change did not require visual transition')


