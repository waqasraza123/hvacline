import hashlib
import secrets


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=32768, r=8, p=3,
        dklen=64, maxmem=64 * 1024 * 1024,
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt$v1${salt.hex()}${_derive(password, salt).hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    salt, expected = bytes(16), bytes(64)
    valid = False
    if encoded is not None:
        parts = encoded.split("$")
        if len(parts) == 4 and parts[:2] == ["scrypt", "v1"]:
            try:
                salt, expected = bytes.fromhex(parts[2]), bytes.fromhex(parts[3])
                valid = len(salt) == 16 and len(expected) == 64
            except ValueError:
                valid = False
    if not valid:
        salt, expected = bytes(16), bytes(64)
    matches = secrets.compare_digest(_derive(password, salt), expected)
    return valid and matches
