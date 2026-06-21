"""Encryption utilities for sensitive data like API keys."""
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the configured encryption key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"agentpilot-api-key-salt",
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.encryption_key.encode()))
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value, returning a base64-encoded ciphertext."""
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


def is_encrypted(value: str) -> bool:
    """Check if a value appears to be encrypted (starts with 'enc:' prefix)."""
    return value.startswith("enc:") if value else False


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key with a prefix for identification."""
    if not api_key or is_encrypted(api_key):
        return api_key
    return "enc:" + encrypt_value(api_key)


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt an API key, handling both encrypted and plaintext formats."""
    if not encrypted:
        return ""
    if is_encrypted(encrypted):
        return decrypt_value(encrypted[4:])
    return encrypted  # Plaintext fallback for migration
