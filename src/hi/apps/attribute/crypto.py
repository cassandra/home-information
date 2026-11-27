import logging

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def get_cipher() -> Fernet:
    """Retrieves the master key from settings and initializes Fernet."""
    return Fernet(settings.ENCRYPTION_KEY)


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
    except InvalidToken:
        logger.warning("Failed to decrypt value. Assuming legacy plain text.")
        return encrypted_text