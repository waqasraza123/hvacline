from insurance_operations.customer_access.passwords import hash_password, verify_password


def test_customer_password_hashes_are_salted_and_verified() -> None:
    password = "fictional account passphrase"
    first = hash_password(password)
    second = hash_password(password)
    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password("a different fictional passphrase", first)


def test_missing_or_malformed_account_hash_cannot_authenticate() -> None:
    assert not verify_password("fictional account passphrase", None)
    assert not verify_password("fictional account passphrase", "invalid")
