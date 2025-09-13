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
