from hi.apps.attribute.attribute_enums import AttributeEnums

from .constants import DIVID


def constants_context(request):
    return {
        'DIVID': DIVID,
        'ATTRIBUTE_ENUMS': AttributeEnums().attribute_enums_map,
    }
