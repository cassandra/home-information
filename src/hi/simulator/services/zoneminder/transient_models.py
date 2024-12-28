from dataclasses import dataclass
from datetime import datetime
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.entity.enums import EntityType, EntityStateType

from hi.simulator.base_models import SimEntityFields, SimState, SimEntityDefinition


@dataclass( frozen = True )
class ZmServerSimEntityFields( SimEntityFields ):
    pass


@dataclass
class ZmServerRunState( SimState ):

    sim_entity_fields  : ZmServerSimEntityFields
    entity_state_type  : EntityStateType  = EntityStateType.DISCRETE
    value              : str              = 'Home'

    @property
    def name(self):
        return 'ZoneMinder Run State'

    
@dataclass( frozen = True )
class ZmMonitorSimEntityFields( SimEntityFields ):

    monitor_id   : int         = None
    status       : str         = 'Connected'
    type         : str         = 'Remote'
    function     : str         = 'Modect'
    protocol     : str         = 'rtsp'
    method       : str         = 'rtpRtsp'
    host         : str         = '192.168.100.204'
    port         : str         = '554'
    path         : str         = 'live3.sdp'
    width        : str         = '1280'
    height       : str         = '800'
    orientation  : str         = 'ROTATE_0'

    def to_api_dict(self):
        return {
            'Monitor': {
                'Id': str(self.monitor_id),
                'Name': self.name,
                'Notes': '',
                'ServerId': '0',
                'StorageId': '0',
                'Type': self.type,
                'Function': self.function,
                'Enabled': '1',
                'LinkedMonitors': None,
                'Triggers': '',
                'Device': '',
                'Channel': '0',
                'Format': '0',
                'V4LMultiBuffer': None,
                'V4LCapturesPerFrame': '1',
                'Protocol': self.protocol,
                'Method': self.method,
                'Host': self.host,
                'Port': self.port,
                'SubPath': '',
                'Path': self.path,
                'Options': None,
                'User': None,
                'Pass': None,
                'Width': self.width,
                'Height': self.height,
                'Colours': '3',
                'Palette': '0',
                'Orientation': self.orientation,
                'Deinterlacing': '0',
                'DecoderHWAccelName': None,
                'DecoderHWAccelDevice': None,
                'SaveJPEGs': '3',
                'VideoWriter': '0',
                'OutputCodec': None,
                'OutputContainer': None,
                'EncoderParameters': '# Lines beginning with # are a comment \r\n# For changing quality, use the crf option\r\n# 1 is best, 51 is worst quality\r\n#crf=23',
                'RecordAudio': '0',
                'RTSPDescribe': False,
                'Brightness': '-1',
                'Contrast': '-1',
                'Hue': '-1',
                'Colour': '-1',
                'EventPrefix': 'Event-',
                'LabelFormat': '%N - %d/%m/%y %H:%M:%S',
                'LabelX': '0',
                'LabelY': '0',
                'LabelSize': '1',
                'ImageBufferCount': '20',
                'WarmupCount': '0',
                'PreEventCount': '5',
                'PostEventCount': '15',
                'StreamReplayBuffer': '0',
                'AlarmFrameCount': '3',
                'SectionLength': '600',
                'MinSectionLength': '10',
                'FrameSkip': '0',
                'MotionFrameSkip': '0',
                'AnalysisFPSLimit': '5.00',
                'AnalysisUpdateDelay': '0',
                'MaxFPS': None,
                'AlarmMaxFPS': None,
                'FPSReportInterval': '100',
                'RefBlendPerc': '6',
                'AlarmRefBlendPerc': '6',
                'Controllable': '0',
                'ControlId': None,
                'ControlDevice': None,
                'ControlAddress': None,
                'AutoStopTimeout': None,
                'TrackMotion': '0',
                'TrackDelay': None,
                'ReturnLocation': '-1',
                'ReturnDelay': None,
                'DefaultRate': '100',
                'DefaultScale': '100',
                'DefaultCodec': 'auto',
                'SignalCheckPoints': '0',
                'SignalCheckColour': '#0000BE',
                'WebColour': '#ec3688',
                'Exif': False,
                'Sequence': '1',
                'TotalEvents': '61',
                'TotalEventDiskSpace': '628452202',
                'HourEvents': '0',
                'HourEventDiskSpace': '0',
                'DayEvents': '1',
                'DayEventDiskSpace': '10711988',
                'WeekEvents': '9',
                'WeekEventDiskSpace': '99347346',
                'MonthEvents': '61',
                'MonthEventDiskSpace': '628452202',
                'ArchivedEvents': '0',
                'ArchivedEventDiskSpace': None,
                'ZoneCount': '5',
                'Refresh': None,
            },
            'Monitor_Status': {
                'MonitorId': str(self.monitor_id),
                'Status': self.status,
                'CaptureFPS': '5.00',
                'AnalysisFPS': '5.00',
                'CaptureBandwidth': '159047',
            }
        }
    
    
@dataclass
class ZmMonitorFunctionState( SimState ):

    sim_entity_fields  : ZmMonitorSimEntityFields
    entity_state_type  : EntityStateType  = EntityStateType.DISCRETE
    value              : str              = 'Modect'

    @property
    def name(self):
        return 'Monitor Function'

    
@dataclass
class ZmMonitorMotionState( SimState ):

    sim_entity_fields  : ZmMonitorSimEntityFields
    entity_state_type  : EntityStateType  = EntityStateType.MOVEMENT

    @property
    def name(self):
        return 'Camera Motion'

    
@dataclass
class ZmStateDefinition:

    monitor_id        : int
    monitor_function  : str

    def to_api_str(self):
        return f'{self.monitor_id}:{self.monitor_function}:1'

    
@dataclass
class ZmState:

    zm_state_id      : int
    name             : str
    definition_list  : List[ ZmStateDefinition ]
    is_active        : bool

    def to_api_dict(self):
        if self.is_active:
            is_active_str = '1'
        else:
            is_active_str = '0'
        return {
            'State': {
                'Id': str(self.zm_state_id),
                'Name': self.name,
                'Definition': ','.join([ x.to_api_str() for x in self.definition_list ]),
                'IsActive': is_active_str,
            },
        }
    
    
@dataclass
class ZmEvent:

    zm_monitor      : ZmMonitorSimEntityFields
    event_id        : int
    start_datetime  : datetime
    end_datetime    : datetime
    name            : str
    cause           : str
    length_secs     : float
    total_frames    : int
    alarm_frames    : int
    total_score     : int
    average_score   : int
    max_score       : int
    
    def to_api_dict(self):
        start_datetime_str = self.start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        if self.end_datetime:
            end_datetime_str = self.end_datetime.strftime('%Y-%m-%d %H:%M:%S')
        else:
            end_datetime_str = None
        date_str = datetimeproxy.to_date_str( self.start_datetime )
        return {
            'Event': {
                'Id': str(self.event_id),
                'MonitorId': str(self.zm_monitor.monitor_id),
                'StorageId': '0',
                'SecondaryStorageId': '0',
                'Name': 'Event- 11091',
                'Cause': 'Forced Web',
                'StartTime': start_datetime_str,
                'EndTime': end_datetime_str,
                'Width': self.zm_monitor.width,
                'Height': self.zm_monitor.height,
                'Length': f'{self.length_secs:.2}',
                'Frames': str(self.total_frames),
                'AlarmFrames': str(self.alarm_frames),
                'DefaultVideo': '',
                'SaveJPEGs': '3',
                'TotScore': str(self.total_score),
                'AvgScore': str(self.average_score),
                'MaxScore': str(self.max_score),
                'Archived': '0',
                'Videoed': '0',
                'Uploaded': '0',
                'Emailed': '0',
                'Messaged': '0',
                'Executed': '0',
                'Notes': f'{self.cause}: ',
                'StateId': '2',
                'Orientation': self.zm_monitor.orientation,
                'DiskSpace': '27303821',
                'Scheme': 'Medium',
                'Locked': False,
                'MaxScoreFrameId': '577976',
                'FileSystemPath': f'/var/cache/zoneminder/events/{self.zm_monitor.monitor_id}/{date_str}/{self.event_id}',
            }
        }

    
@dataclass
class ZmPagination:

    page      : int

    def to_api_dict(self):
        return {
            'page': self.page,
            'current': self.page,
            'count': 1,
            'prevPage': False,
            'nextPage': False,
            'pageCount': 1,
            'order': {
                'Event.StartTime': 'desc'
            },
            'limit': 100,
            'options': {
                'order': {
                    'Event.StartTime': 'desc'
                },
                'sort': 'StartTime',
                'direction': 'desc'
            },
            'paramType': 'querystring',
            'queryScope': None,
        }


ZONEMINDER_SIM_ENTITY_DEFINITION_LIST = [
    SimEntityDefinition(
        class_label = 'Camera (monitor)',
        entity_type = EntityType.MOTION_SENSOR,
        sim_entity_fields_class = ZmMonitorSimEntityFields,
        sim_state_class_list = [
            ZmMonitorFunctionState,
            ZmMonitorMotionState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'ZoneMinder Service',
        entity_type = EntityType.SERVICE,
        sim_entity_fields_class = ZmServerSimEntityFields,
        sim_state_class_list = [
            ZmServerRunState,
        ]
    ),
]
