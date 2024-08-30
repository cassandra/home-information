from hi.apps.common.enums import LabeledEnum
from hi.apps.common.svg_models import SvgViewBox


class CollectionType(LabeledEnum):

    DEFAULT   = ( 'Default', '' )
    ZONE      = ( 'Zone', '' )

    @classmethod
    def default(cls):
        return cls.DEFAULT

    @property
    def svg_bounding_box(self):
        """
        This defines the bounding box of the SVG, which we need to properly
        position, rotate and scale the icon.
        """
        # TODO: Change this after creating initial icons
        return SvgViewBox( x = 0, y = 0, width = 32, height = 32 )
    
    @property
    def svg_icon_template_name(self):
        # TODO: Change this after creating initial icons
        #
        #    return f'templates/entity/svg/type.{self.name.lower()}.svg'
        return 'entity/svg/type.other.svg'
