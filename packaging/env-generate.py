#!/usr/bin/env python3

import os
import secrets
import stat
import shutil
import string

from dataclasses import dataclass


@dataclass
class EmailSettings:
    email_address   : str
    password  : str
    host      : str
    port      : str
    use_tls   : bool
    use_ssl   : bool
        
    
class HiEnvironmentGenerator:

    SECRETS_DIRECTORY = '.private/env'
    
    DEFAULT_SETTINGS = {
        'DJANGO_SETTINGS_MODULE': 'hi.settings.local',
        'HI_SUPPRESS_AUTHENTICATION':'true',
        'HI_REDIS_HOST': '127.0.0.1',
        'HI_REDIS_PORT': '6379',
        'HI_REDIS_KEY_PREFIX': 'local',
        'HI_EMAIL_SUBJECT_PREFIX': '',
        'HI_DB_PATH': '/data/database',  # Docker container location
        'HI_MEDIA_PATH': '/data/media',  # Docker container location
    }

    def __init__( self, env_name = 'local' ):
        self._env_name = env_name

        self._settings_map = dict()
        self._settings_map.update( self.DEFAULT_SETTINGS )
        
        self._destination_filename = os.path.join( self.SECRETS_DIRECTORY, f'{self._env_name}.sh' )
        return
    
    def setup_secrets_directory(self):
        if not os.path.exists( self.SECRETS_DIRECTORY ):
            print( f'Creating directory: {self.SECRETS_DIRECTORY}' )
            os.makedirs( self.SECRETS_DIRECTORY, exist_ok = True )
            os.chmod( self.SECRETS_DIRECTORY, stat.S_IRWXU )  # Read/write/execute for user only
        return
    
    def check_existing_env_file(self):

        if os.path.exists( self._destination_filename ):
            print( f'WARNING: {self._destination_filename} already exists.' )
            overwrite = input( 'Do you want to overwrite it? (y/n): ').strip().lower()
            if overwrite not in ['yes', 'y']:
                print( 'Env file generation cancelled.' )
                exit(1)

            backup_filename = f'{self._destination_filename}.BAK'
            print(f'Creating backup: {backup_filename}')
            shutil.copy2(self._destination_filename, backup_filename)
        return
    
    def generate_env_file( self ):

        self.setup_secrets_directory()
        self.check_existing_env_file()
        
        email_settings = self.get_email_settings()

        django_admin_email = email_settings.email_address
        django_admin_password = self.generate_memorable_password()
        
        from_email = email_settings.email_address
        server_email = email_settings.email_address
        
        self._settings_map['DJANGO_SECRET_KEY'] = self.generate_secret_key()
        self._settings_map['DJANGO_SUPERUSER_EMAIL'] = django_admin_email
        self._settings_map['DJANGO_SUPERUSER_PASSWORD'] = django_admin_password
        self._settings_map['HI_DEFAULT_FROM_EMAIL'] = from_email
        self._settings_map['HI_SERVER_EMAIL'] = server_email
        self._settings_map['HI_EMAIL_HOST'] = email_settings.host
        self._settings_map['HI_EMAIL_PORT'] = email_settings.port
        self._settings_map['HI_EMAIL_HOST_USER'] = email_settings.email_address
        self._settings_map['HI_EMAIL_HOST_PASSWORD'] = email_settings.password
        self._settings_map['HI_EMAIL_USE_TLS'] = str(email_settings.use_tls)
        self._settings_map['HI_EMAIL_USE_SSL'] = str(email_settings.use_ssl)
        
        self.write_file()

        print( '\nYour Django admin credentials:' )
        print( f'  Email: {django_admin_email}' )
        print( f'  Password: {django_admin_password}\n' )
        return
    
    def get_email_settings(self):

        print( 'We need email settings to set up the Django configuration file.' )
        
        email_address = input('Enter your email address: ').strip()
        password = input('Enter your email password: ').strip()

        domain = email_address.split('@')[-1]

        settings = None
        if domain in self.COMMON_EMAIL_PROVIDER_SETTINGS:
            use_predefined = input( f'Used predefined settings for {domain}? (y/n) ' )
            if use_predefined.strip().lower() == 'y':
                settings = self.COMMON_EMAIL_PROVIDER_SETTINGS[domain]
        else:
            print( f'Unknown email provider: {domain}.' )
                
        if not settings:
            print( 'Please provide SMTP settings.' )
            settings = {
                'host': input('Enter SMTP host: ').strip(),
                'port': input('Enter SMTP port: ').strip(),
                'use_tls': input('Use TLS (Y/n): ').strip().lower() != 'n',
                'use_ssl': input('Use SSL (y/N): ').strip().lower() == 'y',
            }

        return EmailSettings(
            email_address = email_address,
            password = password,
            host = settings['host'],
            port = settings['port'],
            use_tls = settings['use_tls'],
            use_ssl = settings['use_ssl'],
        )
    
    def generate_memorable_password( self, num_words = 2, separator = "-" ):

        words = [
            'apple', 'banana', 'cherry', 'delta', 'eagle', 'falcon', 'grape', 
            'hunter', 'island', 'joker', 'kitten', 'lemon', 'melon', 'ninja', 'ocean'
        ]

        chosen_words = [ secrets.choice(words) for _ in range(num_words) ]
        random_number = str( secrets.randbelow( 100 ))  # A number between 0-99
        chosen_words.append( str(random_number) )
            
        password = separator.join(chosen_words)
        return password

    def write_file( self ):
        with open( self._destination_filename, 'w' ) as fh:
            for name, value in self._settings_map.items():
                fh.write( f'export {name}="{value}"\n' )
                continue
        print( f'File created: {self._destination_filename}' )
        return
    
    def generate_secret_key( self, length : int = 50 ):
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(chars) for _ in range(length))

    COMMON_EMAIL_PROVIDER_SETTINGS = {
        'gmail.com': {
            'host': 'smtp.gmail.com',
            'port': '587',
            'use_tls': True,
            'use_ssl': False,
        },
        'yahoo.com': {
            'host': 'smtp.mail.yahoo.com',
            'port': '465',
            'use_tls': False,
            'use_ssl': True,
        },
        'outlook.com': {
            'host': 'smtp.office365.com',
            'port': '587',
            'use_tls': True,
            'use_ssl': False,
        },
        'hotmail.com': {
            'host': 'smtp.office365.com',
            'port': '587',
            'use_tls': True,
            'use_ssl': False,
        },
        'icloud.com': {
            'host': 'smtp.mail.me.com',
            'port': '587',
            'use_tls': True,
            'use_ssl': False,
        },
        'aol.com': {
            'host': 'smtp.aol.com',
            'port': '587',
            'use_tls': True,
            'use_ssl': False,
        },
        'zoho.com': {
            'host': 'smtp.zoho.com',
            'port': '587',
            'use_tls': True,
            'use_ssl': False,
        },
        'protonmail.com': {
            'host': '127.0.0.1',  # Requires the ProtonMail Bridge app
            'port': '1025',  # Default for ProtonMail Bridge
            'use_tls': True,
            'use_ssl': False,
        },
        'yandex.com': {
            'host': 'smtp.yandex.com',
            'port': '465',
            'use_tls': False,
            'use_ssl': True,
        },
        'fastmail.com': {
            'host': 'smtp.fastmail.com',
            'port': '465',
            'use_tls': False,
            'use_ssl': True,
        },
        # Mail.com
        'mail.com': {
            'host': 'smtp.mail.com',
            'port': '587',
            'use_tls': True,
            'use_ssl': False,
        },
    }
        

if __name__ == "__main__":
    
    generator = HiEnvironmentGenerator()
    generator.generate_env_file()
