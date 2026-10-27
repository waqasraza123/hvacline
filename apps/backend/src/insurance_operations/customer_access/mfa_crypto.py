import base64
import hashlib
import hmac
import json
import secrets
import struct
from urllib.parse import quote, urlencode
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken

ISSUER = "HVACLine AI"


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def hotp(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * ((-len(secret)) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 1_000_000).zfill(6)


def valid_totp_counter(secret: str, code: str, now: float, last_counter: int | None) -> int | None:
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    accepted: int | None = None
    for counter in range(max(0, int(now // 30) - 1), int(now // 30) + 2):
        matches = hmac.compare_digest(hotp(secret, counter), code)
        if matches and (last_counter is None or counter > last_counter):
            accepted = counter
    return accepted


def provisioning_uri(email: str, secret: str) -> str:
    return "otpauth://totp/" + quote(f"{ISSUER}:{email}", safe="") + "?" + urlencode({
        "secret": secret, "issuer": ISSUER, "algorithm": "SHA1", "digits": "6", "period": "30",
    }, quote_via=quote)


class MfaVault:
    def __init__(self, key: str) -> None:
        self.cipher = Fernet(key.encode())
        self.recovery_key = hmac.new(
            base64.urlsafe_b64decode(key), b"hvacline/mfa/recovery/v1", hashlib.sha256
        ).digest()

    def encrypt(self, secret: str, context: str) -> str:
        return self.cipher.encrypt(json.dumps({"context": context, "secret": secret}).encode()).decode()

    def decrypt(self, ciphertext: str, context: str) -> str:
        try:
            data = json.loads(self.cipher.decrypt(ciphertext.encode()))
            if not isinstance(data, dict) or data.get("context") != context or not isinstance(data.get("secret"), str):
                raise ValueError("Invalid MFA secret context")
            if len(data["secret"]) != 32 or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for character in data["secret"]):
                raise ValueError("Invalid MFA secret format")
            return str(data["secret"])
        except (InvalidToken, ValueError, TypeError, KeyError) as error:
            raise ValueError("MFA configuration could not be decrypted") from error

    def recovery_hash(self, account_id: UUID, code: str) -> str:
        return hmac.new(self.recovery_key,
                        f"{account_id}:{code.replace('-', '').casefold()}".encode(),
                        hashlib.sha256).hexdigest()


def new_recovery_codes() -> list[str]:
    codes: list[str] = []
    for _ in range(10):
        raw = secrets.token_hex(16)
        codes.append("-".join(raw[index:index + 8] for index in range(0, 32, 8)))
    return codes
