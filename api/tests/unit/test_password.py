from app.shared.authentication.password import PasswordHasher


async def test_hash_and_verify(hasher: PasswordHasher) -> None:
    hashed = await hasher.hash("correct horse")
    assert hashed != "correct horse"
    assert await hasher.verify("correct horse", hashed) is True
    assert await hasher.verify("wrong horse", hashed) is False


async def test_verify_without_hash_is_false(hasher: PasswordHasher) -> None:
    assert await hasher.verify("dummy-password", None) is False
