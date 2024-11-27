import json

from .zm_models import ZmEvent, ZmDetails, ZmEventDetails


class SensorResponseHelper:

    @classmethod
    def event_to_details( cls, zm_event : ZmEvent ) -> str:
        event_details = {
            'event_id': zm_event.event_id,
            'notes': zm_event.notes,
            'duration_secs': zm_event.duration_secs,
            'total_frames': zm_event.total_frame_count,
            'alarmed_frames': zm_event.alarmed_frame_count,
            'score': zm_event.score,
        }
        return json.dumps( event_details )
 
    @classmethod
    def from_details( cls, details : str ) -> ZmDetails:
        details_dict = json.loads( details )
        if 'event_id' in details_dict:
            return ZmEventDetails(
                event_id = details_dict.get('event_id'),
                notes = details_dict.get('notes'),
                duration_secs = details_dict.get('duration_secs'),
                total_frames = details_dict.get('total_frames'),
                alarmed_frames = details_dict.get('alarmed_frames'),
                score = details_dict.get('score'),  
            )
        return None
    
