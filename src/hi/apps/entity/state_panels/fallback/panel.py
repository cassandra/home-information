from hi.apps.entity.enums import DisplayContext
from hi.apps.entity.state_panel_base import EntityStatePanel


modal_panel = EntityStatePanel(
    name             = 'fallback_modal',
    entity_type      = None,
    display_contexts = { DisplayContext.MODAL },
    priority         = 1000,
    template_name    = 'entity/state_panels/fallback/modal.html',
)

list_panel = EntityStatePanel(
    name             = 'fallback_list',
    entity_type      = None,
    display_contexts = { DisplayContext.LIST },
    priority         = 1000,
    template_name    = 'entity/state_panels/fallback/list.html',
)

grid_panel = EntityStatePanel(
    name             = 'fallback_grid',
    entity_type      = None,
    display_contexts = { DisplayContext.GRID },
    priority         = 1000,
    template_name    = 'entity/state_panels/fallback/grid.html',
)
