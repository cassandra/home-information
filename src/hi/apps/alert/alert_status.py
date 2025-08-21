from dataclasses import dataclass
from typing import ClassVar, List

from django.http import HttpRequest

from hi.apps.audio.audio_signal import AudioSignal

from .alert import Alert
from .alert_helpers import AlertHelpers


@dataclass
class AlertStatusData:

    ALERT_LIST_BANNER_TEMPLATE_NAME = 'alert/panes/alert_list_banner.html'
    
    alert_list              : List[ Alert ]
    max_audio_signal        : AudioSignal
    new_audio_signal        : AudioSignal  # Not seen before (for immediate audio notification)

    NewAudioSignalNameAttr  : ClassVar  = 'newAudioSignalName'
    MaxAudioSignalNameAttr  : ClassVar  = 'maxAudioSignalName'
    AlarmMessageHtmlAttr    : ClassVar  = 'alarmMessageHtml'

    def to_dict(self, request : HttpRequest ):
        import logging
        logger = logging.getLogger(__name__)

        alert_list_html_str = AlertHelpers.alert_list_to_html_str(
            request = request,
            alert_list = self.alert_list,
        )
        response_dict = dict()
                
        if self.max_audio_signal:
            response_dict[self.MaxAudioSignalNameAttr] = self.max_audio_signal.label
            logger.debug(f"Added max_audio_signal: {self.max_audio_signal.label}")
            
        if self.new_audio_signal:            
            response_dict[self.NewAudioSignalNameAttr] = self.new_audio_signal.label
            logger.debug(f"Added new_audio_signal: {self.new_audio_signal.label}")
            
        if self.alert_list:
            response_dict[self.AlarmMessageHtmlAttr] = alert_list_html_str
            
        return response_dict
