from hi.apps.entity.enums import DisplayContext, EntityType
from hi.apps.entity.state_panel_base import EntityStatusPanel


modal_panel = EntityStatusPanel(
    name             = 'camera_modal',
    entity_type      = EntityType.CAMERA,
    display_contexts = { DisplayContext.MODAL },
    priority         = 100,
    template_name    = 'entity/state_panels/camera/modal.html',
)

list_panel = EntityStatusPanel(
    name             = 'camera_list',
    entity_type      = EntityType.CAMERA,
    display_contexts = { DisplayContext.LIST },
    priority         = 100,
    template_name    = 'entity/state_panels/camera/list.html',
)

grid_panel = EntityStatusPanel(
    name             = 'camera_grid',
    entity_type      = EntityType.CAMERA,
    display_contexts = { DisplayContext.GRID },
    priority         = 100,
    template_name    = 'entity/state_panels/camera/grid.html',
)
