import os
from cryptography.fernet import Fernet

_fernet = None

def _get_fernet():
    global _fernet
    if _fernet is None:
        _fernet = Fernet(os.getenv("FERNET_KEY").encode())
    return _fernet

def encrypt_message(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()

def decrypt_message(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()
