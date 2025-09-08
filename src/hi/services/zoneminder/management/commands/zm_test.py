from .pyzm_client import api as zmapi
import traceback

from django.core.management.base import BaseCommand

from hi.apps.common.command_utils import CommandLoggerMixin


class Command( BaseCommand, CommandLoggerMixin ):
    """ Used for ad-hoc testing and explorations during development of the Zoneminder integration. """
    
    help = 'Check ZoneMinder API functionality.'

    def handle(self, *args, **options):
        self.info( 'ZoneMinder Test' )

        cam_name = 'FrontCamera'

        api_options = {
            'apiurl': 'https://bordeaux:8443/zm/api',
            'portalurl': 'https://bordeaux:8443/zm',
            'user': 'admin',
            'password': '--REDACTED--',  # TODO: Need to manually tweak this.
            # 'disable_ssl_cert_check': True
        }
        try:
            zmApi = zmapi.ZMApi(options=api_options)
        except Exception as e:
            self.error( 'Error: {}'.format(str(e)) )
            self.info( traceback.format_exc() )
            exit(1)

        self.info("--------| Getting Monitors |-----------")
        ms = zmApi.monitors()
        for m in ms.list():
            self.info('Name:{} Enabled:{} Type:{} Dims:{}'.format( m.name(),
                                                                   m.enabled(),
                                                                   m.type(),
                                                                   m.dimensions()))
            self.info(m.status())
            continue
        
        self.info( "--------| Getting Events |-----------" )
        event_filter = {
            'from': '24 hours ago',  # this will use localtimezone, use 'tz' for other timezones
            'object_only': False,
            'min_alarmed_frames': 1,
            'max_events': 5,
        }                  
        self.info( "Getting events across all monitors" )
        es = zmApi.events(event_filter)
        self.info('I got {} events'.format(len(es.list())))

        self.info('Getting events for {} with filter: {}'.format( cam_name, event_filter))
        cam_events = ms.find( name = cam_name ).events(options=event_filter)
        for e in cam_events.list():
            self.info('Event:{} Cause:{} Notes:{}'.format(e.name(), e.cause(), e.notes()))
            continue
        
        self.info("--------| Getting ZM States |-----------")
        states = zmApi.states()
        for state in states.list():
            self.info('State:{}[{}], active={}, details={}'.format(state.name(), state.id(), state.active(), state.definition()))

        i = input('Test Monitor State Change? [y/N]').lower()
        if i == 'y':
            self.info("--------| Setting Monitors |-----------")
            m = ms.find( name = cam_name )
            try:
                old_function = m.function()
                input('Going to change state of {}[{}] to Monitor from {}'.format(m.name(),m.id(), old_function))
                self.info(m.set_parameter(options={'function':'Monitor'}))
                input('Switching back to {}'.format(old_function))
                self.info(m.set_parameter(options={'function':old_function}))
            except Exception as e:
                self.info('Error: {}'.format(str(e)))

            self.info("--------| Setting Alarms |-----------")
            try:
                input('Arming {}, press enter'.format(m.name()))
                self.info(m.arm())
                input('Disarming {}, press enter'.format(m.name()))
                self.info(m.disarm())
            except Exception as e:
                self.info('Error: {}'.format(str(e)))

        i = input('Test ZM State Changes? [y/N]').lower()
        if i == 'y':
            self.info("--------| Setting States |-----------")
            try:
                input('Stopping ZM press enter')
                self.info(zmApi.stop())
                input('Starting ZM press enter')
                self.info(zmApi.start())
                for idx,state in enumerate(states.list()):
                    self.info('{}:{}'.format(idx,state.name()))
                i = int(input('enter state number to switch to:'))
                name = states.list()[i].name()
                self.info('Changing state to: {}'.format(name))
                self.info(zmApi.set_state(state=name))
            except Exception as e:
                self.info('Error: {}'.format(str(e)))

        self.info("--------| Configs Test |-----------")
        try:
            conf = zmApi.configs()
            self.info(conf.find(name='ZM_AUTH_HASH_LOGINS'))
        except Exception as e:
            self.info('Error: {}'.format(str(e)))

        return
