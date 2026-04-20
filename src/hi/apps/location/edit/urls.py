from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^add$', 
             views.LocationAddView.as_view(), 
             name='location_edit_location_add'),

    re_path( r'^edit-mode/(?P<location_id>\d+)$', 
             views.LocationEditModeView.as_view(), 
             name='location_edit_mode' ),

    re_path( r'^view/edit-mode/(?P<location_view_id>\d+)$', 
             views.LocationViewEditModeView.as_view(), 
             name='location_view_edit_mode' ),

    re_path( r'^item/edit-mode/(?P<html_id>[\w\-]+)$', 
             views.LocationItemEditModeView.as_view(), 
             name='location_item_edit_mode' ),

    re_path( r'^location/properties/edit/(?P<location_id>\d+)$', 
             views.LocationPropertiesEditView.as_view(), 
             name='location_properties_edit'),

    re_path( r'^svg/replace/(?P<location_id>\d+)$', 
             views.LocationSvgReplaceView.as_view(), 
             name='location_edit_svg_replace'),

    re_path( r'^delete/(?P<location_id>\d+)$', 
             views.LocationDeleteView.as_view(), 
             name='location_edit_location_delete' ),

    re_path( r'^view/add$', 
             views.LocationViewAddView.as_view(), 
             name='location_edit_location_view_add' ),

    re_path( r'^view/geometry/(?P<location_view_id>\d+)$', 
             views.LocationViewGeometryView.as_view(), 
             name='location_edit_location_view_geometry' ),

    re_path( r'^view/delete/(?P<location_view_id>\d+)$', 
             views.LocationViewDeleteView.as_view(), 
             name='location_edit_location_view_delete' ),

    re_path( r'^view/manage-item$', 
             views.LocationViewManageItemsView.as_view(), 
             name='location_edit_location_view_manage_items' ),

    re_path( r'^view/entity/toggle/(?P<location_view_id>\d+)/(?P<entity_id>\d+)$', 
             views.LocationViewEntityToggleView.as_view(), 
             name='location_edit_location_view_entity_toggle' ),

    re_path( r'^view/collection/toggle/(?P<location_view_id>\d+)/(?P<collection_id>\d+)$', 
             views.LocationViewCollectionToggleView.as_view(), 
             name='location_edit_location_view_collection_toggle' ),

    re_path( r'^item/position/(?P<html_id>[\w\-]+)$', 
             views.LocationItemPositionView.as_view(), 
             name='location_edit_location_item_position' ),

    re_path( r'^item/path/(?P<html_id>[\w\-]+)$', 
             views.LocationItemPathView.as_view(), 
             name='location_edit_location_item_path' ),
    
    re_path( r'^svg/background/(?P<location_id>\d+)$',
             views.LocationSvgBackgroundView.as_view(),
             name='location_svg_background'),

    re_path( r'^svg/template/(?P<location_id>\d+)$',
             views.LocationSvgTemplateSelectView.as_view(),
             name='location_svg_template_select'),

    re_path( r'^svg/edit/(?P<location_id>\d+)$',
             views.LocationSvgEditView.as_view(),
             name='location_edit_svg_edit'),

    re_path( r'^svg/edit/cancel/(?P<location_id>\d+)$', 
             views.LocationSvgEditCancelView.as_view(), 
             name='location_svg_edit_cancel'),

    re_path( r'^svg/edit/exit/(?P<location_id>\d+)$',
             views.LocationSvgEditExitView.as_view(),
             name='location_svg_edit_exit'),

    re_path( r'^svg/edit/viewbox/(?P<location_id>\d+)$',
             views.LocationSvgEditViewBoxView.as_view(),
             name='location_svg_edit_viewbox'),

    re_path( r'^svg/edit/revert/(?P<location_id>\d+)$',
             views.LocationSvgEditRevertView.as_view(),
             name='location_svg_edit_revert'),

    re_path( r'^svg/edit/save/(?P<location_id>\d+)$',
             views.LocationSvgEditSaveView.as_view(),
             name='location_svg_edit_save'),

    re_path( r'^svg/edit/export/(?P<location_id>\d+)$',
             views.LocationSvgEditExportView.as_view(),
             name='location_svg_edit_export'),

    re_path( r'^svg/edit/help$',
             views.LocationSvgEditHelpView.as_view(),
             name='location_svg_edit_help'),

]
