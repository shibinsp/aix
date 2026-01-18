"""AES-256 encryption for secure API key storage."""
import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import structlog

from app.core.config import settings

logger = structlog.get_logger()


def _get_encryption_key() -> bytes:
    """Derive a Fernet-compatible key from the SECRET_KEY."""
    # Use PBKDF2 to derive a proper 32-byte key from SECRET_KEY
    salt = b"cyberx_api_key_salt"  # Static salt - the SECRET_KEY provides entropy
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key


def get_fernet() -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    return Fernet(_get_encryption_key())


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for secure storage.

    Args:
        api_key: The plaintext API key

    Returns:
        Base64-encoded encrypted key
    """
    if not api_key:
        return ""

    fernet = get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """
    Decrypt an encrypted API key.

    Args:
        encrypted_key: The base64-encoded encrypted key

    Returns:
        The plaintext API key, or None if decryption fails
    """
    if not encrypted_key:
        return None

    try:
        fernet = get_fernet()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except (ValueError, base64.binascii.Error) as e:
        logger.error(f"Failed to decode encrypted key: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        return None


def get_key_hint(api_key: str) -> str:
    """
    Get a hint (last 4 characters) for an API key.

    Args:
        api_key: The plaintext API key

    Returns:
        Last 4 characters of the key for identification
    """
    if not api_key or len(api_key) < 4:
        return "****"
    return f"...{api_key[-4:]}"


def hash_for_comparison(value: str) -> str:
    """
    Create a hash for comparing values without storing plaintext.

    Args:
        value: The value to hash

    Returns:
        SHA-256 hash of the value
    """
    return hashlib.sha256(value.encode()).hexdigest()
