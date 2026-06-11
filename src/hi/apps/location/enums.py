from hi.apps.common.enums import LabeledEnum


class LocationViewType(LabeledEnum):
    """View-level intent for a LocationView. Drives which interactions
    are offered on an entity icon tap: AUTOMATION enables one-click
    control; DEFAULT and SECURITY route to the EntityStatus modal;
    INFORMATION routes to the EntityEdit modal (entity details/config)
    even when the entity has states. For AUTOMATION and INFORMATION a
    long-press is the escape hatch back to the EntityStatus modal.
    Per-entity state selection (visual primary, one-click target) is
    handled by the role-based orderings in
    ``hi.apps.entity.entity_state_role_order``."""

    DEFAULT     = ( 'Default'    , '' )
    SECURITY    = ( 'Security'   , '' )
    AUTOMATION  = ( 'Automation' , '' )
    INFORMATION = ( 'Information', '' )


class SvgItemType(LabeledEnum):

    ICON         = ( 'Icon', '' )
    OPEN_PATH    = ( 'Open Path ', '' )
    CLOSED_PATH  = ( 'Closed Path ', '' )

    @property
    def is_icon(self):
        return bool( self == SvgItemType.ICON )

    @property
    def is_path(self):
        return bool( self in [ SvgItemType.OPEN_PATH, SvgItemType.CLOSED_PATH ] )

    @property
    def is_path_closed(self):
        return bool( self == SvgItemType.CLOSED_PATH )

    
class SvgStyleName(LabeledEnum):

    COLOR      = ( 'Color', '' )
    GREYSCALE  = ( 'Grey Scale ', '' )

    @property
    def svg_defs_template_name(self):
        return f'location/panes/svg_fill_patterns_{self}.html'

    @property
    def css_static_file_name(self):
        return f'css/svg-location-{self}.css'
