from .constants import DIVID


def constants_context(request):
    return {
        'DIVID': DIVID,
        'TIMEZONE_NAME_LIST': [
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
        ],
    }
