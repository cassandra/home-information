from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.utils import str_to_bool

from hi.simulator.base_models import SimEntityFields, SimState, SimEntityDefinition
from hi.simulator.enums import SimEntityType, SimStateType
from hi.simulator.sim_entity import SimEntity

from .constants import ZmSimConstants
from .enums import ZmMonitorFunction, ZmRunStateType


@dataclass( frozen = True )
class ZmServerSimEntityFields( SimEntityFields ):
    name  : str  = 'ZM Server'


@dataclass
class ZmServerRunState( SimState ):

    sim_entity_fields  : ZmServerSimEntityFields
    sim_state_type     : SimStateType             = SimStateType.DISCRETE
    sim_state_id       : str                      = 'runstate'
    value              : str                      = ZmRunStateType.default_value()

    @property
    def name(self):
        return 'ZoneMinder Run State'

    @property
    def choices(self) -> List[ Tuple[ str, str ]]:
        return ZmRunStateType.choices()

    
@dataclass( frozen = True )
class ZmSimServer:
    """ Wrapper to encapsulate ZmServer-specific accessors """
    
    sim_entity    : SimEntity

    @property
    def run_state_value(self) -> str:
        for sim_state in self.sim_entity.sim_state_list:
            if isinstance( sim_state, ZmServerRunState ):
                return sim_state.value
            continue
        raise ValueError( 'No run state found for ZM server entity.' )


@dataclass
class ZmSimRunStateDefinition:

    monitor_id        : int
    monitor_function  : str

    def to_api_str(self):
        return f'{self.monitor_id}:{self.monitor_function}:1'

        
@dataclass
class ZmSimRunState:

    zm_run_state_id  : int
    name             : str
    definition_list  : List[ ZmSimRunStateDefinition ]
    is_active        : bool

    def to_api_dict(self):
        if self.is_active:
            is_active_str = '1'
        else:
            is_active_str = '0'
        return {
            'State': {
                'Id': str(self.zm_run_state_id),
                'Name': self.name,
                'Definition': ','.join([ x.to_api_str() for x in self.definition_list ]),
                'IsActive': is_active_str,
            },
        }
    
    
@dataclass( frozen = True )
class ZmMonitorSimEntityFields( SimEntityFields ):

    monitor_id   : int         = None
    status       : str         = 'Connected'
    type         : str         = 'Remote'
    function     : str         = ZmMonitorFunction.default_value()
    protocol     : str         = 'rtsp'
    method       : str         = 'rtpRtsp'
    host         : str         = '192.168.100.204'
    port         : str         = '554'
    path         : str         = 'live3.sdp'
    width        : str         = '1280'
    height       : str         = '800'
    orientation  : str         = 'ROTATE_0'

    
@dataclass( frozen = True )
class ZmSimMonitor:
    """ Wrapper to encapsulate ZmMonitor-specific accessors """

    sim_entity    : SimEntity

    @property
    def monitor_id(self):
        return self.sim_entity.sim_entity_fields.monitor_id

    @property
    def width(self):
        return self.sim_entity.sim_entity_fields.width

    @property
    def height(self):
        return self.sim_entity.sim_entity_fields.height

    @property
    def orientation(self):
        return self.sim_entity.sim_entity_fields.orientation

    @property
    def motion_sim_state(self) -> SimState:
        for sim_state in self.sim_entity.sim_state_list:
            if isinstance( sim_state, ZmMonitorMotionState ):
                return sim_state
            continue
        raise ValueError( f'No motion sim state for ZM monitor {self.sim_entity}' )
    
    def to_api_dict(self):
        fields = self.sim_entity.sim_entity_fields

        monitor_function = ZmMonitorFunction.default_value()
        for sim_state in self.sim_entity.sim_state_list:
            if isinstance( sim_state, ZmMonitorFunctionState ):
                monitor_function = sim_state.value
            continue
        
        return {
            'Monitor': {
                'Id': str(fields.monitor_id),
                'Name': fields.name,
                'Notes': '',
                'ServerId': '0',
                'StorageId': '0',
                'Type': fields.type,
                'Function': monitor_function,
                'Enabled': '1',
                'LinkedMonitors': None,
                'Triggers': '',
                'Device': '',
                'Channel': '0',
                'Format': '0',
                'V4LMultiBuffer': None,
                'V4LCapturesPerFrame': '1',
                'Protocol': fields.protocol,
                'Method': fields.method,
                'Host': fields.host,
                'Port': fields.port,
                'SubPath': '',
                'Path': fields.path,
                'Options': None,
                'User': None,
                'Pass': None,
                'Width': fields.width,
                'Height': fields.height,
                'Colours': '3',
                'Palette': '0',
                'Orientation': fields.orientation,
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
                'MonitorId': str(fields.monitor_id),
                'Status': fields.status,
                'CaptureFPS': '5.00',
                'AnalysisFPS': '5.00',
                'CaptureBandwidth': '159047',
            }
        }
    
    
@dataclass
class ZmMonitorFunctionState( SimState ):

    sim_entity_fields  : ZmMonitorSimEntityFields
    sim_state_type     : SimStateType              = SimStateType.DISCRETE
    sim_state_id       : str                       = 'function'
    value              : str                       = ZmMonitorFunction.default_value()

    @property
    def choices(self) -> List[ Tuple[ str, str ]]:
        return ZmMonitorFunction.choices()

    @property
    def name(self):
        return 'Monitor Function'

    
@dataclass
class ZmMonitorMotionState( SimState ):

    sim_entity_fields  : ZmMonitorSimEntityFields
    sim_state_type     : SimStateType              = SimStateType.MOVEMENT
    sim_state_id       : str                       = 'motion'

    @property
    def name(self):
        return 'Camera Motion'

    def set_value_from_string( self, value_str : str ):
        self.value = str_to_bool( value_str )
        return

    
@dataclass
class ZmSimEvent:

    zm_sim_monitor  : ZmSimMonitor
    event_id        : int
    start_datetime  : datetime
    end_datetime    : datetime
    name            : str
    cause           : str        = 'Simulator',
    length_secs     : float      = 0.0
    total_frames    : int        = 0
    alarm_frames    : int        = 0
    total_score     : int        = 0
    average_score   : int        = 0
    max_score       : int        = 0

    @property
    def is_active(self):
        return bool( self.end_datetime is None )

    def update_score_properties( self ):
        if self.end_datetime:
            now_datetime = self.end_datetime
        else:
            now_datetime = datetimeproxy.now()

        duration_timedelta = now_datetime - self.start_datetime

        self.length_secs = float( duration_timedelta.seconds )

        # TODO: Setting these somewhat randomly and with specicic event
        # characteristics.  Only will need to change this if we need
        # finer-grained control over the simulation.

        frame_per_second = 5
        self.total_frames = int( duration_timedelta.seconds * frame_per_second )
        self.alarm_frames = int( self.total_frames / 2 )
        self.total_score = int( self.alarm_frames * 10 )
        self.average_score = int( self.alarm_frames * 5 )
        self.max_score = int( self.alarm_frames * 20 )
        return
        
    def to_api_dict(self):
        tz_adjusted_start_datetime = datetimeproxy.change_timezone(
            original_datetime = self.start_datetime,
            new_tzname = ZmSimConstants.TIMEZONE_NAME,
        )
        start_datetime_str = tz_adjusted_start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        if self.end_datetime:
            tz_adjusted_end_datetime = datetimeproxy.change_timezone(
                original_datetime = self.end_datetime,
                new_tzname = ZmSimConstants.TIMEZONE_NAME,
            )
            end_datetime_str = tz_adjusted_end_datetime.strftime('%Y-%m-%d %H:%M:%S')
        else:
            end_datetime_str = None
        date_str = datetimeproxy.to_date_str( self.start_datetime )
        return {
            'Event': {
                'Id': str(self.event_id),
                'MonitorId': str(self.zm_sim_monitor.monitor_id),
                'StorageId': '0',
                'SecondaryStorageId': '0',
                'Name': 'Event- 11091',
                'Cause': 'Forced Web',
                'StartTime': start_datetime_str,
                'EndTime': end_datetime_str,
                'Width': self.zm_sim_monitor.width,
                'Height': self.zm_sim_monitor.height,
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
                'Orientation': self.zm_sim_monitor.orientation,
                'DiskSpace': '27303821',
                'Scheme': 'Medium',
                'Locked': False,
                'MaxScoreFrameId': '577976',
                'FileSystemPath': f'/var/cache/zoneminder/events/{self.zm_sim_monitor.monitor_id}/{date_str}/{self.event_id}',
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
        sim_entity_type = SimEntityType.MOTION_SENSOR,
        sim_entity_fields_class = ZmMonitorSimEntityFields,
        sim_state_class_list = [
            ZmMonitorFunctionState,
            ZmMonitorMotionState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'ZoneMinder Service',
        sim_entity_type = SimEntityType.SERVICE,
        sim_entity_fields_class = ZmServerSimEntityFields,
        sim_state_class_list = [
            ZmServerRunState,
        ]
    ),
]
