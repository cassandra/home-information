#!/usr/bin/env python3

import argparse
import os
import re
import secrets
import stat
import shutil
import string
import sys

from dataclasses import dataclass

    
@dataclass
class SmtpSettings:
    host     : str
    port     : int
    use_tls  : bool
    use_ssl  : bool

    @property
    def is_valid(self):
        if not self.host:
            return False
        if not self.is_valid_port( self.port ):
            return False
        if not self.is_valid_encryption( use_tls = self.use_tls, use_ssl = self.use_ssl ):
            return False
        return True

    @staticmethod
    def is_valid_port( port: str ) -> bool:
        try:
            port_number = int( port )
            if ( port_number < 1 ) or ( port_number > 65535 ):
                return False
        except (TypeError, ValueError):
            return False
        return True
    
    @staticmethod
    def is_valid_encryption( use_tls: bool, use_ssl : bool ) -> bool:
        if use_tls and use_ssl:
            return False
        if not use_tls and not use_ssl:
            return False
        return True


@dataclass
class EmailSettings:
    email_address  : str
    password       : str
    smtp_settings  : SmtpSettings

    @property
    def is_valid(self):
        if not bool( self.email_address and self.password ):
            return False
        return self.smtp_settings.is_valid

    @staticmethod
    def is_valid_email( email: str ) -> bool:
        # This is approximate, not fully validating to specification.
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        return bool( re.match( email_regex, email ))

    
class HiEnvironmentGenerator:

    SECRETS_DIRECTORY = '.private/env'
    DEFAULT_ADMIN_EMAIL = 'admin@example.com'
    DOCKER_DATA_DIRECTORY = '/data'
    NON_DOCKER_DATA_DIRECTORY_DEFAULT = 'data'

    DJANGO_SERVER_PORT_DEFAULT = '8000'
    DJANGO_SERVER_PORT_MAP = {
        'development': '8411',
    }

    SH_FILE_SUFFIX = 'sh'
    ENV_FILE_SUFFIX = 'env'
    
    def __init__( self,
                  env_name  : str = 'local',
                  verbose   : bool = False ):

        if env_name not in [ 'development', 'local', 'staging', 'production' ]:
            self.print_warning( f'Non-standard environment name "{env_name}".'
                                f' Ensure that the file "hi/settings/{env_name}.py" exists.' )
        
        self._env_name = env_name
        self._verbose = verbose
        
        self._settings_map = {
            'DJANGO_SETTINGS_MODULE': f'hi.settings.{self._env_name}',
            'HI_SUPPRESS_AUTHENTICATION':'true',
            'HI_REDIS_HOST': '127.0.0.1',
            'HI_REDIS_PORT': '6379',
            'HI_REDIS_KEY_PREFIX': '',
            'HI_EMAIL_SUBJECT_PREFIX': '',
            'HI_EXTRA_HOST_URLS': '',  # To be filled in manually if/when running beyond localhost
            'HI_EXTRA_CSP_URLS': '',  # To be filled in manually if/when running beyond localhost
        }
        self._settings_map['DJANGO_SERVER_PORT'] = self.DJANGO_SERVER_PORT_MAP.get(
            self._env_name,
            self.DJANGO_SERVER_PORT_DEFAULT,
        )

        self._destination_filename = os.path.join( self.SECRETS_DIRECTORY,
                                                   f'{self._env_name}.{self.ENV_FILE_SUFFIX}' )
        
        if self._env_name not in [ 'local' ]:
            self._settings_map['HI_REDIS_KEY_PREFIX'] = self._env_name
            self._settings_map['HI_EMAIL_SUBJECT_PREFIX'] = f'[{self._env_name}] '
            self._destination_filename = os.path.join( self.SECRETS_DIRECTORY,
                                                       f'{self._env_name}.{self.SH_FILE_SUFFIX}' )
        return
    
    def generate_env_file( self ):

        if self._env_name == 'production':
            print( '\n* ERROR * This script should not be used to generate production settings!\n' )
            return

        self.print_important(
            'About:\n'
            '\nThis script will help you generate your initial environment variables.'
            '\nYou usually only need to run this once.'
            '\nNone of the choices you make here are final.'
            '\nYou can modify any of the settings directly in the generated file.'
        )
        
        self._setup_secrets_directory()
        self._check_existing_env_file()

        db_dir, media_dir = self._get_data_directories()
        self._settings_map['HI_DB_PATH'] = db_dir
        self._settings_map['HI_MEDIA_PATH'] = media_dir

        email_settings = self._get_email_settings()

        # Emails are required for signin since it uses emailed codes, not passwords.
        if email_settings.is_valid:
            require_signin = self.input_boolean( 'Configure to require user sign in?', default = False )
            if require_signin:
                self._settings_map['HI_SUPPRESS_AUTHENTICATION'] = 'false'
        
        django_admin_email = email_settings.email_address
        django_admin_password = self._generate_memorable_password()
        
        from_email = email_settings.email_address
        server_email = email_settings.email_address

        self._settings_map['DJANGO_SECRET_KEY'] = self._generate_secret_key()
        self._settings_map['DJANGO_SUPERUSER_EMAIL'] = django_admin_email
        self._settings_map['DJANGO_SUPERUSER_PASSWORD'] = django_admin_password
        self._settings_map['HI_DEFAULT_FROM_EMAIL'] = from_email
        self._settings_map['HI_SERVER_EMAIL'] = server_email
        self._settings_map['HI_EMAIL_HOST_USER'] = email_settings.email_address
        self._settings_map['HI_EMAIL_HOST_PASSWORD'] = email_settings.password
        self._settings_map['HI_EMAIL_HOST'] = email_settings.smtp_settings.host
        self._settings_map['HI_EMAIL_PORT'] = str(email_settings.smtp_settings.port)
        self._settings_map['HI_EMAIL_USE_TLS'] = str(email_settings.smtp_settings.use_tls)
        self._settings_map['HI_EMAIL_USE_SSL'] = str(email_settings.smtp_settings.use_ssl)
        
        self._write_file()

        self.print_important( f'Review your settings file: {self._destination_filename}' )
        self.print_important( 'Your Django admin credentials:'
                              f'\n    Email: {django_admin_email}'
                              f'\n    Password: {django_admin_password}' )
        return
    
    def _setup_secrets_directory( self ):
        if not os.path.exists( self.SECRETS_DIRECTORY ):
            self.print_notice( f'Creating directory: {self.SECRETS_DIRECTORY}' )
            os.makedirs( self.SECRETS_DIRECTORY, exist_ok = True )
            os.chmod( self.SECRETS_DIRECTORY, stat.S_IRWXU )  # Read/write/execute for user only
        elif not os.path.isdir( self.SECRETS_DIRECTORY ):
            self.print_warning( 'Secrets area "{self.SECRETS_DIRECTORY}" needs to be a directory.' )
            exit(1)
        return
    
    def _check_existing_env_file( self ):

        if os.path.exists( self._destination_filename ):
            self.print_warning( f'WARNING: {self._destination_filename} already exists.' )
            overwrite = self.input_boolean( 'Do you want to overwrite it?', default = False )
            if not overwrite:
                self.print_warning( 'Env file generation cancelled.' )
                exit(1)

            backup_filename = f'{self._destination_filename}.BAK'
            if os.path.exists( backup_filename ):
                os.rename( backup_filename, f'{backup_filename}.BAK' )
            self.print_notice( f'Creating backup: {backup_filename}' )
            shutil.copy2( self._destination_filename, backup_filename )
        return

    def _get_data_directories( self ):
        if self._env_name in [ 'local' ]:
            return ( f'{self.DOCKER_DATA_DIRECTORY}/database',
                     f'{self.DOCKER_DATA_DIRECTORY}/media' )

        self.print_important( 'Data Directory:\n'
                              '\nDefine a data directory for your database and uploaded "media" files.'
                              '\nThis script assumes these two will live in the same directory.'
                              '\nYou can alter this manually in the generated file if needed.' )

        while True:
            input_path = self.input_string( 'Enter your data directory',
                                            default = self.NON_DOCKER_DATA_DIRECTORY_DEFAULT )
            expanded_path = os.path.expanduser( input_path )
            if os.path.isabs( expanded_path ):
                data_dir = expanded_path
            else:
                data_dir = os.path.abspath( expanded_path )  
                
            database_dir = f'{data_dir}/database'
            media_dir = f'{data_dir}/media'
            if not os.path.exists( data_dir ):
                self.print_warning( f'The directory "{data_dir}" does not exist.' )
                should_create = self.input_boolean( 'Do you want to create it?', default = False )
                if not should_create:
                    continue
                os.makedirs( database_dir, exist_ok = True )
                os.makedirs( media_dir, exist_ok = True )
                return ( database_dir, media_dir )
            
            elif not os.path.isdir( data_dir ):
                self.print_warning( f'The path "{data_dir}" exists, but it is not a directory.' )
                continue
            
            else:
                if not os.path.exists( database_dir ):
                    os.makedirs( database_dir, exist_ok = True )
                if not os.path.exists( media_dir ):
                    os.makedirs( media_dir, exist_ok = True )
                return ( database_dir, media_dir )
            continue
        return
        
    def _get_email_settings( self ) -> EmailSettings:

        use_email = self.input_boolean( 'Configure email to allow alert notifications?', default = False )
        if use_email:
            self.print_notice( 'You may have to tweak your email provider\'s settings to allow this.' )
        else:
            return EmailSettings(
                email_address = self.DEFAULT_ADMIN_EMAIL,
                password = '',
                smtp_settings = SmtpSettings(
                    host = '',
                    port = '',
                    use_tls = False,
                    use_ssl = False,
                ),
            )

        while True:
            email_address = self.input_string( 'Enter your email address' )
            if EmailSettings.is_valid_email( email_address ):
                break
            self.print_warning( f'Invalid email address: {email_address}' )
            continue

        while True:
            password = self.input_string( 'Enter your email password' )
            if password:
                break
            self.print_warning( 'Password canot be empty' )
            continue

        domain = email_address.split('@')[-1]

        smtp_settings = None
        if domain in self.COMMON_EMAIL_PROVIDER_SETTINGS:
            use_predefined = self.input_boolean( f'Used predefined settings for {domain}?' )
            if use_predefined:
                smtp_settings = self.COMMON_EMAIL_PROVIDER_SETTINGS[domain]
                
        if not smtp_settings:
            self.print_notice( 'Please provide SMTP settings.' )
            smtp_settings = self._get_smtp_settings()
            
        return EmailSettings(
            email_address = email_address,
            password = password,
            smtp_settings = smtp_settings,
        )

    def _get_smtp_settings( self ) -> SmtpSettings:
        while True:
            host = self.input_string('Enter SMTP email host')
            if host:
                break
            self.print_warning( 'Host name canot be empty' )
            continue

        use_tls = self.input_boolean( 'SMTP server uses TLS (STARTTLS)', default = True )
        if use_tls:
            use_ssl = False
            default_port = 587
        else:
            use_ssl = True
            default_port = 465

        while True:
            port = self.input_string('Enter SMTP port', default = str(default_port) )
            if SmtpSettings.is_valid_port( port ):
                break
            self.print_warning( f'Invalid port "{port}". Must be an integer in range [ 1024, 65535 ]' )
            continue
        
        return SmtpSettings(
            host = host,
            port = port,
            use_tls = use_tls,
            use_ssl = use_ssl,
        )
        
    def _generate_memorable_password( self, num_words : int = 2, separator : str = "-" ):

        words = [
            'apple', 'banana', 'cherry', 'delta', 'eagle', 'falcon', 'grape', 
            'hunter', 'island', 'joker', 'kitten', 'lemon', 'melon', 'ninja', 'ocean'
        ]

        chosen_words = [ secrets.choice(words) for _ in range(num_words) ]
        random_number = str( secrets.randbelow( 100 ))  # A number between 0-99
        chosen_words.append( str(random_number) )
            
        password = separator.join(chosen_words)
        return password

    def _write_file( self ):

        is_sh_file = self._destination_filename.endswith( self.SH_FILE_SUFFIX )
        with open( self._destination_filename, 'w' ) as fh:
            for name, value in self._settings_map.items():
                value = str(value)  # ensure string
                if is_sh_file:
                    escaped_value = value.replace("\\", "\\\\")  # Escape backslashes FIRST
                    escaped_value = escaped_value.replace("\"", "\\\"")
                    escaped_value = escaped_value.replace("$", "\\$")
                    escaped_value = escaped_value.replace("`", "\\`")
                    fh.write( f'export {name}="{escaped_value}"\n' )
                else:
                    fh.write( f'{name}={value}\n' )
                continue
        self.print_success( f'File created: {self._destination_filename}' )

        if self._verbose:
            self.print_debug( 'Files contents:' )
            print( '----------')
            with open( self._destination_filename, 'r' ) as fh:
                print( fh.read(), end = '' )
            print('----------')    
        return
    
    def _generate_secret_key( self, length : int = 50 ):
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(chars) for _ in range(length))

    @classmethod
    def input_boolean( cls, message : str, default : bool = None ) -> bool:

        if default is not None:
            if default:
                prompt = '[Y/n]'
            else:
                prompt = '[y/N]'
        else:
            prompt = '[y/n]'
            
        while True:
            value_str = input( f'{message} {prompt}: ').strip().lower()
            if not value_str and default is not None:
                return default
            if value_str in [ 'y', 'yes' ]:
                return True
            elif value_str in [ 'n', 'no' ]:
                return False
            cls.print_warning( 'Please answer "y" or "n".' )
            continue
        
    @classmethod
    def input_string( cls, message : str, default : str = None ) -> str:
        if default:
            prompt = f'[{default}]'
        else:
            prompt = ''
        value = input( f'{message} {prompt}: ' ).strip()
        if not value and default is not None:
            return default
        return value
    
    @staticmethod
    def print_debug( message : str ):
        print( f'[DEBUG] {message}' )

    @staticmethod
    def print_notice( message : str ):
        print( f'\n[NOTICE] {message}\n' )

    @staticmethod
    def print_warning( message : str ):
        print( f'\n\033[96m[WARNING]\033[0m {message}\n' )  # Yellow text

    @staticmethod
    def print_success( message : str ):
        print( f'\033[32m[SUCCESS]\033[0m {message}' )  # Green text

    @staticmethod
    def print_important(message: str):
        lines = message.split('\n')
        max_width = min( 80, max( len(line) for line in lines ) + 6 )

        def pad_line( line ):
            return line.center( max_width )

        padded_lines = [ pad_line(line) for line in lines ]
        border = " " * max_width

        # Inverted fg/bg text
        print( f'\n\033[7m{border}\033[0m' )
        for padded_line in padded_lines:
            print( f'\033[7m{padded_line}\033[0m' )
            continue
        print( f'\033[7m{border}\033[0m\n' )
        return

    @staticmethod
    def zzzprint_important( message : str ):
        border = '=' * ( min( len(message), 74 ) + 6)
        print( f'\n\033[7m{border}\033[0m' )  # Blue border
        print( f'\033[7m{message}\033[0m' )  # Blue text
        print( f'\033[7m{border}\033[0m\n' )  # Blue border
        
    COMMON_EMAIL_PROVIDER_SETTINGS = {
        'gmail.com': SmtpSettings(
            host = 'smtp.gmail.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'yahoo.com': SmtpSettings(
            host = 'smtp.mail.yahoo.com',
            port = 465,
            use_tls = False,
            use_ssl = True,
        ),
        'outlook.com': SmtpSettings(
            host = 'smtp.office365.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'hotmail.com': SmtpSettings(
            host = 'smtp.office365.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'icloud.com': SmtpSettings(
            host = 'smtp.mail.me.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'aol.com': SmtpSettings(
            host = 'smtp.aol.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'zoho.com': SmtpSettings(
            host = 'smtp.zoho.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
        'protonmail.com': SmtpSettings(
            host = '127.0.0.1',  # Requires the ProtonMail Bridge app
            port = 1025,  # Default for ProtonMail Bridge
            use_tls = True,
            use_ssl = False,
        ),
        'fastmail.com': SmtpSettings(
            host = 'smtp.fastmail.com',
            port = 465,
            use_tls = False,
            use_ssl = True,
        ),
        'mail.com': SmtpSettings(
            host = 'smtp.mail.com',
            port = 587,
            use_tls = True,
            use_ssl = False,
        ),
    }


def parse_command_line_args():
    
    parser = argparse.ArgumentParser(
        description = 'Generate environment variables for Home Information.',
        add_help = True,
    )
    parser.add_argument(
        '--env-name',
        type = str,
        default = 'local',
        help = 'Name of the environment file to generate (default: "local").',
    )
    parser.add_argument(
        '--verbose',
        action = 'store_true',
        help = 'Enable verbose output for debugging purposes.',
    )

    args, unknown = parser.parse_known_args()

    if unknown:
        print( f'[ERROR] Unrecognized arguments: {" ".join(unknown)}\n' )
        parser.print_help()
        sys.exit(1)

    if not args.env_name.isidentifier():
        print( '[ERROR] Environment name must be a valid Python identifier.' )
        sys.exit(1)

    return args


if __name__ == '__main__':

    args = parse_command_line_args()
    generator = HiEnvironmentGenerator(
        env_name = args.env_name,
        verbose = args.verbose,
    )
    generator.generate_env_file()
    
