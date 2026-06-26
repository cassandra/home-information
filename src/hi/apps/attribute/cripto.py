import logging

from django.conf import settings
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def get_cipher():
    """Retrieves the master key from settings and initializes Fernet."""
    key = getattr(settings, 'MASTER_ENCRYPTION_KEY', None)
    if not key:
        logger.critical("Security misconfiguration: MASTER_ENCRYPTION_KEY is not defined in settings.")
        raise ValueError("The MASTER_ENCRYPTION_KEY setting is not defined.")
    return Fernet(key)


def encrypt_value(plain_text: str) -> str:
    """Encrypts plain text and returns a string representation."""
    if not plain_text:
        return plain_text
        
    cipher = get_cipher()
    return cipher.encrypt(plain_text.encode('utf-8')).decode('utf-8')


def decrypt_value(encrypted_text: str) -> str:
    """Decrypts the encrypted string and returns the original plain text."""
    if not encrypted_text:
        return encrypted_text
        
    cipher = get_cipher()
    try:
        return cipher.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.warning("Unable to decrypt value.")
        raise ValueError("Unable to decrypt value.") from e