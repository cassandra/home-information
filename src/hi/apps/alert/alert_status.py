from dataclasses import dataclass
from typing import ClassVar, List

from hi.apps.config.enums import AudioSignal

from .alert import Alert


@dataclass
class AlertStatusData:

    alert_list              : List[ Alert ]
    max_audio_signal        : AudioSignal
    new_audio_signal        : AudioSignal  # Not seen before (for immediate audio notification)

    NewAudioSignalNameAttr  : ClassVar  = 'newAudioSignalName'
    MaxAudioSignalNameAttr  : ClassVar  = 'maxAudioSignaName'
    AlarmMessageHtmlAttr    : ClassVar  = 'alarmMessageHtml'

    def to_dict(self):


        
        # TODO: alarm_list to HTML via new template
        


        response_dict = dict()
        if self.max_audio_signal:
            response_dict[self.MaxAudioSignalNameAttr] = str(self.max_audio_signal)
        if self.new_audio_signal:            
            response_dict[self.NewAudioSignalNameAttr] = str(self.new_audio_signal)
        if self.alert_list:
            response_dict[self.AlarmMessageHtmlAttr] = zzz
        return response_dict
