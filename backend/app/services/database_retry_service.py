"""
=========================================================
Database Retry Service
=========================================================

Provides controlled retry handling for transient database
connection/timeout failures.

Security / Reliability Requirement
----------------------------------
Database Timeout -> Retry (3x)

Design
------
- Maximum of 3 attempts.
- Retries only transient SQLAlchemy DB failures.
- Integrity/application errors are NOT retried.
- Rolls back the SQLAlchemy session after a failed attempt.
- Uses the existing SQLAlchemy session.
- Does not introduce database schema changes.
- Keeps transaction logic inside the calling service.

Important
---------
A database commit can potentially succeed even when the
client loses the connection while receiving the response.

Therefore this service only retries failures that are
classified as connection/operational failures by SQLAlchemy.
=========================================================
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError

from backend.app.extensions import db


class DatabaseRetryService:
    """
    Controlled retry handler for transient database failures.
    """

    MAX_ATTEMPTS = 3

    RETRY_DELAY_SECONDS = 0.25

    @classmethod
    def _is_retryable_error(
        cls,
        error: Exception,
    ) -> bool:
        """
        Determine whether a database error is safe to retry.

        Retry:
            - OperationalError
            - DBAPIError with an invalidated connection

        Do not retry:
            - IntegrityError
            - ordinary application errors
            - non-database exceptions
        """

        if isinstance(
            error,
            IntegrityError,
        ):
            return False

        if isinstance(
            error,
            OperationalError,
        ):
            return True

        if isinstance(
            error,
            DBAPIError,
        ):
            return bool(
                getattr(
                    error,
                    "connection_invalidated",
                    False,
                )
            )

        return False

    @classmethod
    def execute(
        cls,
        operation: Callable[[], Any],
        max_attempts: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a database operation with controlled retry.

        Parameters
        ----------
        operation:
            Callable containing the database transaction.

        max_attempts:
            Maximum number of attempts.
            Defaults to MAX_ATTEMPTS and is capped at 3.

        Returns
        -------
        dict
            {
                "success": True,
                "attempts": 1,
                "result": operation_result,
            }

        Raises
        ------
        Exception
            The final database/application exception after
            retry handling is exhausted.
        """

        if max_attempts is None:
            max_attempts = cls.MAX_ATTEMPTS

        if not isinstance(
            max_attempts,
            int,
        ):
            raise ValueError(
                "max_attempts must be an integer."
            )

        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least 1."
            )

        max_attempts = min(
            max_attempts,
            cls.MAX_ATTEMPTS,
        )

        attempts = 0

        while attempts < max_attempts:

            attempts += 1

            try:

                result = operation()

                return {
                    "success": True,
                    "attempts": attempts,
                    "result": result,
                }

            except Exception as error:

                retryable = (
                    cls._is_retryable_error(
                        error
                    )
                )

                try:
                    db.session.rollback()
                except Exception:
                    pass

                if (
                    not retryable
                    or attempts >= max_attempts
                ):

                    raise

                time.sleep(
                    cls.RETRY_DELAY_SECONDS
                )

        raise RuntimeError(
            "Database retry operation ended unexpectedly."
        )