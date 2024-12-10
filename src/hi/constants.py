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

    'LOCATION_EDIT_PANE': 'hi-location-edit',
    'LOCATION_VIEW_EDIT_PANE': 'hi-location-view-edit',
    'ENTITY_EDIT_PANE': 'hi-entity-edit',
    'COLLECTION_EDIT_PANE': 'hi-collection-edit',
    'ENTITY_POSITION_EDIT_PANE': 'hi-entity-position-edit',
    'COLLECTION_POSITION_EDIT_PANE': 'hi-collection-position-edit',

    'ATTRIBUTE_CONTAINER_CLASS': 'hi-attribute',

    'ALERT_BANNER_CONTAINER': 'hi-alert-banner-container',
    'ALERT_BANNER_CONTENT': 'hi-alert-banner-content',
    'SECURITY_STATE_CONTROL': 'hi-security-state-control',
}
