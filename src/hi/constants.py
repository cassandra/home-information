TIME_OF_DAY_CHOICES = [
    ( f'{hour:02}:{minute:02}',
      f'{hour:02}:{minute:02} ({(hour % 12 or 12):02}:{minute:02} {"a.m." if hour < 12 else "p.m."})' )
    for hour in range(24) for minute in range(0, 60, 15)
]


TIMEZONE_NAME_LIST = [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Toronto',
    'America/Mexico_City',
    'America/Sao_Paulo',
    'Europe/London',
    'Europe/Berlin',
    'Europe/Paris',
    'Europe/Moscow',
    'Asia/Dubai',
    'Asia/Tokyo',
    'Asia/Seoul',
    'Asia/Shanghai',
    'Asia/Hong_Kong',
    'Asia/Singapore',
    'Asia/Kolkata',
    'Asia/Jakarta',
    'Australia/Sydney',
    'Australia/Melbourne',
    'Africa/Johannesburg',
    'Africa/Lagos',
    'Africa/Cairo',
    'America/Argentina/Buenos_Aires',
]

    
# HTML div ids (classes and attributes) that app logic depends on.
DIVID = {

    # Main HI Grid Structure
    'TOP': 'hi-top-content',
    'BOTTOM': 'hi-bottom-content',
    'MAIN': 'hi-main-content',
    'SIDE': 'hi-side-content',

    'LOCATION_PROPERTIES_PANE': 'hi-location-properties',
    'LOCATION_VIEW_EDIT_PANE': 'hi-location-view-edit',
    'COLLECTION_EDIT_PANE': 'hi-collection-edit',
    'ENTITY_PROPERTIES_PANE': 'hi-entity-properties',
    'ENTITY_POSITION_EDIT_PANE': 'hi-entity-position-edit',
    'COLLECTION_POSITION_EDIT_PANE': 'hi-collection-position-edit',

    'ATTRIBUTE_CONTAINER_CLASS': 'hi-attribute',

    'ALERT_BANNER_CONTAINER': 'hi-alert-banner-container',
    'ALERT_BANNER_CONTENT': 'hi-alert-banner-content',
    'SECURITY_STATE_CONTROL': 'hi-security-state-control',
    'WEATHER_OVERVIEW': 'hi-weather-overview',
    'WEATHER_ALERTS': 'hi-weather-alerts',
    
    'CONSOLE_LOCK_BUTTON': 'hi-console-lock-button',
    
    # Entity Attribute Editing V2
    'ATTR_V2_FORM': 'attr-v2-form',
    'ATTR_V2_CONTENT': 'attr-v2-content',
    'ATTR_V2_UPLOAD_FORM_CONTAINER': 'attr-v2-upload-form-container',
    'ATTR_V2_FILE_GRID': 'attr-v2-file-grid',
    'ATTR_V2_STATUS_MSG': 'attr-v2-status-msg',
    'ATTR_V2_DIRTY_MESSAGE': 'attr-v2-dirty-message',
    'ATTR_V2_UPDATE_BTN': 'attr-v2-update-btn',
    'ATTR_V2_MESSAGES': 'attr-v2-messages',
    'ATTR_V2_MODAL_CLASS': 'attr-v2-modal',
    'ATTR_V2_ATTRIBUTE_CARD_CLASS': 'attr-v2-attribute-card',
    'ATTR_V2_NEW_ATTRIBUTE_CLASS': 'attr-v2-new-attribute',
    'ATTR_V2_FILE_TITLE_INPUT_CLASS': 'attr-v2-file-title-input',
    'ATTR_V2_FILE_INFO_CLASS': 'attr-v2-file-info',
    'ATTR_V2_FIELD_DIRTY_CLASS': 'attr-v2-field-dirty',
    'ATTR_V2_DIRTY_INDICATOR_CLASS': 'attr-v2-dirty-indicator',
    'ATTR_V2_ATTRIBUTE_NAME_CLASS': 'attr-v2-attribute-name',
    'ATTR_V2_DELETE_BTN_CLASS': 'attr-v2-delete-btn',
    'ATTR_V2_UNDO_BTN_CLASS': 'attr-v2-undo-btn',
    'ATTR_V2_FILE_CARD_CLASS': 'attr-v2-file-card',
    'ATTR_V2_FILE_NAME_CLASS': 'attr-v2-file-filename',
    'ATTR_V2_SECRET_INPUT_WRAPPER_CLASS': 'attr-v2-secret-input-wrapper',
    'ATTR_V2_SECRET_INPUT_CLASS': 'attr-v2-secret-input',
    'ATTR_V2_ICON_SHOW_CLASS': 'attr-v2-icon-show',
    'ATTR_V2_ICON_HIDE_CLASS': 'attr-v2-icon-hide',
    'ATTR_V2_TEXTAREA_CLASS': 'attr-v2-textarea',
    'ATTR_V2_TEXT_VALUE_WRAPPER_CLASS': 'attr-v2-text-value-wrapper',
    'ATTR_V2_EXPAND_CONTROLS_CLASS': 'attr-v2-expand-controls',
    'ATTR_V2_FILE_INPUT': 'attr-v2-file-input',
    'ATTR_V2_ADD_ATTRIBUTE_BTN': 'attr-v2-add-attribute-btn',
    'ATTR_V2_SCROLLABLE_CONTENT': 'attr-v2-scrollable-content',
}
