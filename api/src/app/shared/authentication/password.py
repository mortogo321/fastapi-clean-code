"""bcrypt hashing, run in a worker thread so it never blocks the event loop."""

import asyncio

import bcrypt


class PasswordHasher:
    def __init__(self, rounds: int) -> None:
        self._rounds = rounds
        # Checked when the email is unknown, so response time does not reveal which emails exist.
        self._dummy_hash = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds))

    async def hash(self, password: str) -> str:
        salt = bcrypt.gensalt(self._rounds)
        hashed = await asyncio.to_thread(bcrypt.hashpw, password.encode(), salt)
        return hashed.decode()

    async def verify(self, password: str, password_hash: str | None) -> bool:
        """Always does the bcrypt work; ``password_hash=None`` (unknown user) never matches."""
        hashed = self._dummy_hash if password_hash is None else password_hash.encode()
        matches = await asyncio.to_thread(bcrypt.checkpw, password.encode(), hashed)
        return matches and password_hash is not None
