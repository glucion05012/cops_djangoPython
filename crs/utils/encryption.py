from cryptography.fernet import Fernet
import base64
from django.conf import settings

# Generate key only once and store in settings.SECRET_KEY or a separate ENCRYPTION_KEY
def get_cipher():
    key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode())
    return Fernet(key)

def encrypt_id(app_id: int) -> str:
    cipher = get_cipher()
    return cipher.encrypt(str(app_id).encode()).decode()

def decrypt_id(encrypted_id: str) -> int:
    cipher = get_cipher()
    return int(cipher.decrypt(encrypted_id.encode()).decode())
