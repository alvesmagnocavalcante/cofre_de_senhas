import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


# Monta o conjunto de chaves de criptografia.
def _cipher():
    configured = [
        key.strip() for key in settings.VAULT_ENCRYPTION_KEYS.split(",") if key.strip()
    ]
    if not configured:
        if not settings.DEBUG:
            raise ImproperlyConfigured("VAULT_ENCRYPTION_KEYS nao configurada.")
        configured = [
            base64.urlsafe_b64encode(
                hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            ).decode()
        ]
    try:
        return MultiFernet([Fernet(key.encode()) for key in configured])
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "VAULT_ENCRYPTION_KEYS contem uma chave Fernet invalida."
        ) from exc


# Criptografia e descriptografia dos campos protegidos.
def encrypt_value(value):
    if not isinstance(value, str) or not value:
        raise ValueError("O segredo nao pode ser vazio.")
    return _cipher().encrypt(value.encode())


def decrypt_value(value):
    try:
        return _cipher().decrypt(bytes(value)).decode()
    except InvalidToken as exc:
        raise ValueError("Nao foi possivel decifrar o segredo.") from exc
