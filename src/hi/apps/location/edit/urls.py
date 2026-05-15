from django.urls import path
from django.urls import re_path

from . import views


urlpatterns = [

    path( 'add',
          views.LocationAddView.as_view(),
          name='location_edit_location_add'),

    path( 'add-first',
          views.LocationAddFirstView.as_view(),
          name='location_edit_location_add_first'),

    path( 'edit-mode/<int:location_id>', 
          views.LocationEditModeView.as_view(), 
          name='location_edit_mode' ),

    path( 'view/edit-mode/<int:location_view_id>', 
          views.LocationViewEditModeView.as_view(), 
          name='location_view_edit_mode' ),

    re_path( r'^item/edit-mode/(?P<html_id>[\w\-]+)$', 
             views.LocationItemEditModeView.as_view(), 
             name='location_item_edit_mode' ),

    path( 'location/properties/edit/<int:location_id>', 
          views.LocationPropertiesEditView.as_view(), 
          name='location_properties_edit'),

    path( 'svg/replace/<int:location_id>', 
          views.LocationSvgReplaceView.as_view(), 
          name='location_edit_svg_replace'),

    path( 'delete/<int:location_id>', 
          views.LocationDeleteView.as_view(), 
          name='location_edit_location_delete' ),

    path( 'view/add', 
          views.LocationViewAddView.as_view(), 
          name='location_edit_location_view_add' ),

    path( 'view/geometry/<int:location_view_id>', 
          views.LocationViewGeometryView.as_view(), 
          name='location_edit_location_view_geometry' ),

    path( 'view/delete/<int:location_view_id>', 
          views.LocationViewDeleteView.as_view(), 
          name='location_edit_location_view_delete' ),

    path( 'view/manage-item', 
          views.LocationViewManageItemsView.as_view(), 
          name='location_edit_location_view_manage_items' ),

    path( 'view/entity/toggle/<int:location_view_id>/<int:entity_id>', 
          views.LocationViewEntityToggleView.as_view(), 
          name='location_edit_location_view_entity_toggle' ),

    path( 'view/collection/toggle/<int:location_view_id>/<int:collection_id>', 
          views.LocationViewCollectionToggleView.as_view(), 
          name='location_edit_location_view_collection_toggle' ),

    re_path( r'^item/position/(?P<html_id>[\w\-]+)$', 
             views.LocationItemPositionView.as_view(), 
             name='location_edit_location_item_position' ),

    re_path( r'^item/path/(?P<html_id>[\w\-]+)$', 
             views.LocationItemPathView.as_view(), 
             name='location_edit_location_item_path' ),
    
    path( 'svg/background/<int:location_id>',
          views.LocationSvgBackgroundView.as_view(),
          name='location_svg_background'),

    path( 'svg/template/<int:location_id>',
          views.LocationSvgTemplateSelectView.as_view(),
          name='location_svg_template_select'),

    path( 'svg/edit/<int:location_id>',
          views.LocationSvgEditView.as_view(),
          name='location_edit_svg_edit'),

    path( 'svg/edit/cancel/<int:location_id>', 
          views.LocationSvgEditCancelView.as_view(), 
          name='location_svg_edit_cancel'),

    path( 'svg/edit/exit/<int:location_id>',
          views.LocationSvgEditExitView.as_view(),
          name='location_svg_edit_exit'),

    path( 'svg/edit/viewbox/<int:location_id>',
          views.LocationSvgEditViewBoxView.as_view(),
          name='location_svg_edit_viewbox'),

    path( 'svg/edit/revert/<int:location_id>',
          views.LocationSvgEditRevertView.as_view(),
          name='location_svg_edit_revert'),

    path( 'svg/edit/save/<int:location_id>',
          views.LocationSvgEditSaveView.as_view(),
          name='location_svg_edit_save'),

    path( 'svg/edit/export/<int:location_id>',
          views.LocationSvgEditExportView.as_view(),
          name='location_svg_edit_export'),

    path( 'svg/edit/help',
          views.LocationSvgEditHelpView.as_view(),
          name='location_svg_edit_help'),

]
