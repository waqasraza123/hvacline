import base64
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from insurance_operations.customer_access.mfa_crypto import (
    MfaVault,
    hotp,
    new_recovery_codes,
    new_totp_secret,
    provisioning_uri,
    valid_totp_counter,
)


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [(59, "287082"), (1111111109, "081804"), (1111111111, "050471"),
     (1234567890, "005924"), (2000000000, "279037"), (20000000000, "353130")],
)
def test_totp_matches_rfc6238_sha1_vectors(timestamp: int, expected: str) -> None:
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert hotp(secret, timestamp // 30) == expected
    assert valid_totp_counter(secret, expected, timestamp, None) == timestamp // 30


def test_totp_rejects_replay_distant_codes_and_non_ascii_digits() -> None:
    secret = new_totp_secret()
    assert len(secret) == 32
    counter = 10000
    for offset in (-1, 0, 1):
        code = hotp(secret, counter + offset)
        assert valid_totp_counter(secret, code, counter * 30, None) == counter + offset
        assert valid_totp_counter(secret, code, counter * 30, counter + 1) is None
    for code in ("１２３４５６", "12345", "1234567", "12 456"):
        assert valid_totp_counter(secret, code, counter * 30, None) is None
    distant = counter + 10
    while hotp(secret, distant) in {hotp(secret, counter + offset) for offset in (-1, 0, 1)}:
        distant += 1
    assert valid_totp_counter(secret, hotp(secret, distant), counter * 30, None) is None


def test_encrypted_seeds_are_bound_to_account_tenant_and_challenge() -> None:
    vault = MfaVault(Fernet.generate_key().decode())
    secret = new_totp_secret()
    context = f"{uuid4()}:{uuid4()}:pending:{uuid4()}"
    ciphertext = vault.encrypt(secret, context)
    assert secret not in ciphertext
    assert vault.decrypt(ciphertext, context) == secret
    with pytest.raises(ValueError):
        vault.decrypt(ciphertext, f"{uuid4()}:{uuid4()}:pending:{uuid4()}")
    with pytest.raises(ValueError):
        MfaVault(Fernet.generate_key().decode()).decrypt(ciphertext, context)
    with pytest.raises(ValueError):
        vault.decrypt(ciphertext[:-8] + "tampered", context)
    uri = provisioning_uri("fictional+customer@example.test", secret)
    assert uri.startswith("otpauth://totp/HVACLine%20AI%3A")
    assert "algorithm=SHA1&digits=6&period=30" in uri


def test_recovery_codes_have_high_entropy_and_account_scoped_hashes() -> None:
    vault = MfaVault(Fernet.generate_key().decode())
    codes = new_recovery_codes()
    assert len(set(codes)) == 10
    account = uuid4()
    for code in codes:
        assert len(bytes.fromhex(code.replace("-", ""))) == 16
        digest = vault.recovery_hash(account, code)
        assert code not in digest
        assert digest == vault.recovery_hash(account, code.upper().replace("-", ""))
        assert digest != vault.recovery_hash(uuid4(), code)
