from django.urls import path, re_path

from . import views


urlpatterns = [
    path( '',
          views.ScenesIndexView.as_view(),
          name = 'simulator_scenes' ),

    path( 'create',
          views.SceneCreateView.as_view(),
          name = 'simulator_scene_create' ),

    path( '<int:scene_id>/rename',
          views.SceneRenameView.as_view(),
          name = 'simulator_scene_rename' ),

    path( '<int:scene_id>/delete',
          views.SceneDeleteView.as_view(),
          name = 'simulator_scene_delete' ),

    path( '<int:scene_id>/apply',
          views.SceneApplyView.as_view(),
          name = 'simulator_scene_apply' ),

    path( 'off',
          views.SceneOffView.as_view(),
          name = 'simulator_scene_off' ),

    path( 'clear-states',
          views.SceneClearStatesView.as_view(),
          name = 'simulator_scene_clear_states' ),

    path( 'clear-states/confirm',
          views.SceneClearStatesConfirmView.as_view(),
          name = 'simulator_scene_clear_states_confirm' ),

    path( 'restore-states',
          views.SceneRestoreStatesView.as_view(),
          name = 'simulator_scene_restore_states' ),

    path( 'status',
          views.SceneStatusView.as_view(),
          name = 'simulator_scene_status' ),

    path( '<int:scene_id>/transport',
          views.SceneTransportView.as_view(),
          name = 'simulator_scene_transport' ),

    path( '<int:scene_id>/states',
          views.SceneEditStatesView.as_view(),
          name = 'simulator_scene_edit_states' ),

    path( '<int:scene_id>/record/start',
          views.SceneRecordStartView.as_view(),
          name = 'simulator_scene_record_start' ),

    path( '<int:scene_id>/stop',
          views.SceneStopView.as_view(),
          name = 'simulator_scene_stop' ),

    path( '<int:scene_id>/record/save',
          views.SceneRecordSaveView.as_view(),
          name = 'simulator_scene_record_save' ),

    path( '<int:scene_id>/record/discard',
          views.SceneRecordDiscardView.as_view(),
          name = 'simulator_scene_record_discard' ),

    path( '<int:scene_id>/play/<int:sequence_id>',
          views.ScenePlayView.as_view(),
          name = 'simulator_scene_play' ),

    path( '<int:scene_id>/step/<int:sequence_id>',
          views.SceneStepView.as_view(),
          name = 'simulator_scene_step' ),

    path( '<int:scene_id>/seek/<int:sequence_id>',
          views.SceneSeekView.as_view(),
          name = 'simulator_scene_seek' ),

    path( '<int:scene_id>/pause',
          views.ScenePauseView.as_view(),
          name = 'simulator_scene_pause' ),

    path( '<int:scene_id>/mark',
          views.SceneMarkView.as_view(),
          name = 'simulator_scene_mark' ),

    path( 'sequence/<int:sequence_id>/delete',
          views.SequenceDeleteView.as_view(),
          name = 'simulator_sequence_delete' ),

    path( 'sequence/<int:sequence_id>/initial/set',
          views.SequenceSetInitialView.as_view(),
          name = 'simulator_sequence_set_initial' ),

    path( 'sequence/<int:sequence_id>/initial/clear',
          views.SequenceClearInitialView.as_view(),
          name = 'simulator_sequence_clear_initial' ),

    path( '<int:scene_id>/sequence/<int:sequence_id>/edit',
          views.SceneSequenceEditView.as_view(),
          name = 'simulator_sequence_edit' ),

    path( '<int:scene_id>/sequence/<int:sequence_id>/export',
          views.SceneSequenceExportView.as_view(),
          name = 'simulator_sequence_export' ),

    path( '<int:scene_id>/sequence/import',
          views.SceneSequenceImportView.as_view(),
          name = 'simulator_sequence_import' ),

    # module_key contains dots/colons, so use a permissive pattern.
    re_path( r'^(?P<scene_id>\d+)/binding/(?P<module_key>[\w_\-\.\:]+)/(?P<profile_id>\d+|none)$',
             views.SceneBindingSetView.as_view(),
             name = 'simulator_scene_binding_set' ),
]
