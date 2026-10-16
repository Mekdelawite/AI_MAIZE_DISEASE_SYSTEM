"""
=========================================================
Upload Rate Limit Service
=========================================================

Protects authenticated image-upload endpoints against
excessive upload attempts.

Security policy:
    - Maximum 10 uploads per user per rolling minute
    - The 11th upload within the same 60-second window
      is rejected
    - One shared service is used by all image-upload routes
    - No database schema changes required

Protected upload flows:
    - /api/diagnosis
    - /api/diagnosis/complete
    - /api/sync
    - /api/sync/batch

Important:
    This is an in-memory protection intended for the current
    application deployment. A shared persistent store such
    as Redis should be used for multi-worker production
    deployments.

=========================================================
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock


class UploadRateLimitService:
    """
    Track authenticated image-upload attempts per user.
    """

    MAX_UPLOADS = 10
    WINDOW_SECONDS = 60

    _records: dict[int, deque[datetime]] = {}
    _lock = Lock()

    @classmethod
    def _now(cls) -> datetime:
        """Return the current UTC time."""
        return datetime.now(timezone.utc)

    @classmethod
    def _cleanup(
        cls,
        user_id: int,
        now: datetime,
    ) -> deque[datetime]:
        """
        Remove timestamps outside the rolling time window.
        """

        timestamps = cls._records.get(
            user_id
        )

        if timestamps is None:
            timestamps = deque()
            cls._records[user_id] = timestamps

        cutoff = (
            now
            - timedelta(
                seconds=cls.WINDOW_SECONDS
            )
        )

        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        return timestamps

    @classmethod
    def check_and_record(
        cls,
        user_id: int,
        upload_count: int = 1,
    ) -> dict[str, int | bool]:
        """
        Check whether the requested upload count is allowed
        and record it when allowed.

        Args:
            user_id:
                Authenticated user's database ID.

            upload_count:
                Number of files being uploaded by this request.
                Defaults to one.

        Returns:
            Dictionary containing:
                allowed
                current_count
                remaining
                retry_after_seconds
        """

        try:
            user_id = int(user_id)
        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "user_id must be an integer."
            ) from error

        try:
            upload_count = int(
                upload_count
            )
        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "upload_count must be an integer."
            ) from error

        if user_id <= 0:
            raise ValueError(
                "user_id must be greater than zero."
            )

        if upload_count <= 0:
            raise ValueError(
                "upload_count must be greater than zero."
            )

        if upload_count > cls.MAX_UPLOADS:
            return {
                "allowed": False,
                "current_count": cls.MAX_UPLOADS,
                "remaining": 0,
                "retry_after_seconds": cls.WINDOW_SECONDS,
            }

        now = cls._now()

        with cls._lock:

            timestamps = cls._cleanup(
                user_id=user_id,
                now=now,
            )

            current_count = len(
                timestamps
            )

            if (
                current_count
                + upload_count
                > cls.MAX_UPLOADS
            ):

                retry_after = (
                    timestamps[0]
                    + timedelta(
                        seconds=cls.WINDOW_SECONDS
                    )
                    - now
                ).total_seconds()

                return {
                    "allowed": False,
                    "current_count": current_count,
                    "remaining": max(
                        cls.MAX_UPLOADS
                        - current_count,
                        0,
                    ),
                    "retry_after_seconds": max(
                        int(retry_after) + 1,
                        1,
                    ),
                }

            for _ in range(upload_count):
                timestamps.append(now)

            return {
                "allowed": True,
                "current_count": (
                    current_count
                    + upload_count
                ),
                "remaining": (
                    cls.MAX_UPLOADS
                    - current_count
                    - upload_count
                ),
                "retry_after_seconds": 0,
            }

    @classmethod
    def clear_user(
        cls,
        user_id: int,
    ) -> None:
        """
        Clear upload-rate state for one user.

        Intended for testing and controlled maintenance.
        """

        try:
            user_id = int(user_id)
        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "user_id must be an integer."
            ) from error

        with cls._lock:
            cls._records.pop(
                user_id,
                None,
            )

    @classmethod
    def clear_all(cls) -> None:
        """
        Clear all upload-rate state.

        Intended for testing and controlled maintenance.
        """

        with cls._lock:
            cls._records.clear()