"""
=========================================================
Login Attempt Service
=========================================================

Protects the login endpoint against repeated invalid
credential attempts.

Security policy:
    - Maximum 5 failed login attempts
    - 5-minute lockout after the limit is reached
    - Successful login clears the failed-attempt counter
    - Lockout is tracked by phone number and client IP
    - No database schema changes required

Important:
    This is an in-memory protection intended for the current
    application deployment. A shared persistent store such
    as Redis should be used for multi-worker production
    deployments.

=========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any


class LoginAttemptService:
    """
    Track failed login attempts and temporary lockouts.
    """

    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 5

    _records: dict[str, dict[str, Any]] = {}
    _lock = Lock()

    @classmethod
    def _now(cls) -> datetime:
        """Return the current UTC time."""
        return datetime.now(timezone.utc)

    @classmethod
    def _normalize_key_part(
        cls,
        value: str | None,
    ) -> str:
        """
        Normalize a key component without exposing it.
        """
        if value is None:
            return ""

        return str(value).strip().lower()

    @classmethod
    def _make_key(
        cls,
        phone_number: str | None,
        client_ip: str | None,
    ) -> str:
        """
        Build a login-attempt tracking key.

        Both phone number and client IP are included so an
        attacker cannot trivially bypass the protection by
        changing only one of them.
        """

        phone = cls._normalize_key_part(
            phone_number
        )

        ip = cls._normalize_key_part(
            client_ip
        )

        return f"{phone}|{ip}"

    @classmethod
    def is_locked(
        cls,
        phone_number: str | None,
        client_ip: str | None,
    ) -> tuple[bool, int]:
        """
        Check whether the login key is currently locked.

        Returns:
            (locked, remaining_seconds)
        """

        key = cls._make_key(
            phone_number,
            client_ip,
        )

        now = cls._now()

        with cls._lock:

            record = cls._records.get(key)

            if record is None:
                return False, 0

            locked_until = record.get(
                "locked_until"
            )

            if locked_until is None:
                return False, 0

            if now >= locked_until:

                cls._records.pop(
                    key,
                    None,
                )

                return False, 0

            remaining = int(
                (
                    locked_until - now
                ).total_seconds()
            )

            return True, max(
                remaining,
                1,
            )

    @classmethod
    def record_failure(
        cls,
        phone_number: str | None,
        client_ip: str | None,
    ) -> dict[str, Any]:
        """
        Record one failed login attempt.

        On the fifth failed attempt, the key is locked
        for LOCKOUT_MINUTES.
        """

        key = cls._make_key(
            phone_number,
            client_ip,
        )

        now = cls._now()

        with cls._lock:

            record = cls._records.get(
                key
            )

            if record is None:
                record = {
                    "attempts": 0,
                    "locked_until": None,
                }

                cls._records[key] = record

            locked_until = record.get(
                "locked_until"
            )

            if (
                locked_until is not None
                and now < locked_until
            ):

                remaining = int(
                    (
                        locked_until - now
                    ).total_seconds()
                )

                return {
                    "locked": True,
                    "attempts": record[
                        "attempts"
                    ],
                    "remaining_seconds": max(
                        remaining,
                        1,
                    ),
                }

            if (
                locked_until is not None
                and now >= locked_until
            ):
                record["attempts"] = 0
                record["locked_until"] = None

            record["attempts"] += 1

            if (
                record["attempts"]
                >= cls.MAX_ATTEMPTS
            ):

                locked_until = (
                    now
                    + timedelta(
                        minutes=cls.LOCKOUT_MINUTES
                    )
                )

                record["locked_until"] = (
                    locked_until
                )

                return {
                    "locked": True,
                    "attempts": record[
                        "attempts"
                    ],
                    "remaining_seconds": (
                        cls.LOCKOUT_MINUTES * 60
                    ),
                }

            return {
                "locked": False,
                "attempts": record[
                    "attempts"
                ],
                "remaining_seconds": 0,
            }

    @classmethod
    def record_success(
        cls,
        phone_number: str | None,
        client_ip: str | None,
    ) -> None:
        """
        Clear failed login attempts after successful login.
        """

        key = cls._make_key(
            phone_number,
            client_ip,
        )

        with cls._lock:
            cls._records.pop(
                key,
                None,
            )

    @classmethod
    def clear_all(cls) -> None:
        """
        Clear all records.

        Intended for testing and controlled maintenance.
        """

        with cls._lock:
            cls._records.clear()