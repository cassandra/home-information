import json
from typing import Dict

from .zm_manager import ZoneMinderManager
from .zm_models import ZmEvent, ZmResponseDetails, ZmEventDetails


class SensorResponseHelper:

    @classmethod
    def event_to_detail_attrs( cls, zm_event : ZmEvent ) -> Dict[ str, str ]:
        return {
            'event_id': zm_event.event_id,
            'notes': zm_event.notes,
            'duration_secs': zm_event.duration_secs,
            'total_frames': zm_event.total_frame_count,
            'alarmed_frames': zm_event.alarmed_frame_count,
            'score': zm_event.score,
            'start_datetime': zm_event.start_datetime.isoformat(),
        }
 
    @classmethod
    def from_details( cls, details : str ) -> ZmResponseDetails:
        details_dict = json.loads( details )
        if 'event_id' in details_dict:
            event_id = details_dict.get('event_id')
            video_stream_url = ZoneMinderManager().get_event_video_stream_url( event_id )
            return ZmEventDetails(
                event_id = event_id,
                notes = details_dict.get('notes'),
                duration_secs = details_dict.get('duration_secs'),
                total_frames = details_dict.get('total_frames'),
                alarmed_frames = details_dict.get('alarmed_frames'),
                score = details_dict.get('score'),
                start_datetime = details_dict.get('start_datetime'),
                video_stream_url = video_stream_url,
            )
        return None
