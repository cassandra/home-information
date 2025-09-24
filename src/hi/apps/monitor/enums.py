from hi.apps.common.enums import LabeledEnum


class EntityDisplayCategory(LabeledEnum):
    """
    Used for styling and layout decisions (e.g., collection templates).
    """

    PLAIN      = ( 'Plain',
                   'Entity with no states or video stream - displays name and icon only')
    HAS_STATE  = ( 'Has State',
                   'Entity with sensor/controller states - displays state data and controls')
    HAS_VIDEO  = ( 'Has Video',
                   'Entity with video stream - displays video player')

    @classmethod
    def default(cls):
        return cls.PLAIN

    def css_class(self) -> str:
        return self.name.lower().replace('_', '-')
