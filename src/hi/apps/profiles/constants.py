VIEW_INTRO_HELP_SESSION_KEY = 'view_intro_help_timestamp'
VIEW_INTRO_HELP_DURATION_SECONDS = 600  # 10 minutes

EDIT_INTRO_HELP_SESSION_KEY = 'edit_intro_help_timestamp'
EDIT_INTRO_HELP_DURATION_SECONDS = 600  # 10 minutes
EDIT_MODE_ENTRY_COUNT_KEY = 'edit_mode_entry_count'

# Profile JSON specification comment constants for self-documenting files
# These comments document the different structural patterns possible in the JSON format

# Entity structural pattern comments - based on JSON structure patterns
ENTITY_COMMENT_ICON_POSITIONED = "Icon-positioned entities (EntityPosition) - most common case"
ENTITY_COMMENT_PATH_ENTITY = "Path entity (EntityPath) - represented by SVG paths"
ENTITY_COMMENT_COLLECTION_MEMBER = "Entities that are part of collections"

# Collection structural pattern comments - based on JSON structure patterns
COLLECTION_COMMENT_WITH_POSITIONING = "Collection with spatial positioning on location views"
COLLECTION_COMMENT_PATH_BASED = "Collection with path representation"

# Profile JSON field name constants to avoid magic strings
# Top-level fields
PROFILE_FIELD_NAME = 'profile_name'
PROFILE_FIELD_DESCRIPTION = 'description'
PROFILE_FIELD_LOCATIONS = 'locations'
PROFILE_FIELD_COLLECTIONS = 'collections'
PROFILE_FIELD_ENTITIES = 'entities'

# Location fields
LOCATION_FIELD_NAME = 'name'
LOCATION_FIELD_SVG_FRAGMENT_FILENAME = 'svg_fragment_filename'
LOCATION_FIELD_SVG_VIEW_BOX_STR = 'svg_view_box_str'
LOCATION_FIELD_ORDER_ID = 'order_id'
LOCATION_FIELD_VIEWS = 'views'

# LocationView fields
LOCATION_VIEW_FIELD_NAME = 'name'
LOCATION_VIEW_FIELD_TYPE_STR = 'location_view_type_str'
LOCATION_VIEW_FIELD_SVG_VIEW_BOX_STR = 'svg_view_box_str'
LOCATION_VIEW_FIELD_SVG_STYLE_NAME_STR = 'svg_style_name_str'
LOCATION_VIEW_FIELD_ORDER_ID = 'order_id'

# Collection fields
COLLECTION_FIELD_NAME = 'name'
COLLECTION_FIELD_TYPE_STR = 'collection_type_str'
COLLECTION_FIELD_VIEW_TYPE_STR = 'collection_view_type_str'
COLLECTION_FIELD_ORDER_ID = 'order_id'
COLLECTION_FIELD_ENTITIES = 'entities'
COLLECTION_FIELD_POSITIONS = 'positions'
COLLECTION_FIELD_PATHS = 'paths'
COLLECTION_FIELD_VISIBLE_IN_VIEWS = 'visible_in_views'

# Entity fields
ENTITY_FIELD_NAME = 'name'
ENTITY_FIELD_TYPE_STR = 'entity_type_str'
ENTITY_FIELD_POSITIONS = 'positions'
ENTITY_FIELD_PATHS = 'paths'
ENTITY_FIELD_VISIBLE_IN_VIEWS = 'visible_in_views'

# Common fields
COMMON_FIELD_COMMENT = 'comment'
COMMON_FIELD_LOCATION_NAME = 'location_name'
COMMON_FIELD_SVG_X = 'svg_x'
COMMON_FIELD_SVG_Y = 'svg_y'
COMMON_FIELD_SVG_SCALE = 'svg_scale'
COMMON_FIELD_SVG_ROTATE = 'svg_rotate'
COMMON_FIELD_SVG_PATH = 'svg_path'
