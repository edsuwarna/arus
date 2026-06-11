import base64
import hashlib

from cryptography.fernet import Fernet

from arus.shared.config import settings


def _derive_key() -> bytes:
    """Derive a consistent Fernet key from JWT secret."""
    raw = settings.jwt_secret.encode() if settings.jwt_secret else b"arus-default-secret-key"
    return base64.urlsafe_b64encode(hashlib.sha256(raw).digest())


def get_fernet() -> Fernet:
    return Fernet(_derive_key())


def encrypt_password(password: str) -> str:
    return get_fernet().encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return get_fernet().decrypt(encrypted.encode()).decode()
