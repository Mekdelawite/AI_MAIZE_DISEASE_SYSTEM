"""
=========================================================
Offline Synchronization Storage Service
=========================================================

Handles permanent storage of images belonging to offline
synchronization operations.

The stored image allows an interrupted synchronization
operation to be recovered after an application crash.

This service is responsible only for file storage.
It does NOT perform image validation or diagnosis.
=========================================================
"""

from __future__ import annotations

import shutil
from pathlib import Path


class SyncStorageError(Exception):
    """Raised when synchronization image storage fails."""


class SyncStorageService:
    """
    Stores offline synchronization images permanently
    until their synchronization lifecycle is complete.
    """

    STORAGE_DIRECTORY_NAME = "sync_images"

    @classmethod
    def get_storage_directory(cls) -> Path:
        """
        Return the permanent synchronization-image directory.
        """

        project_root = Path(__file__).resolve().parents[3]

        storage_directory = (
            project_root
            / "uploads"
            / cls.STORAGE_DIRECTORY_NAME
        )

        storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return storage_directory

    @classmethod
    def store(
        cls,
        source_path: str | Path,
        operation_id: str,
    ) -> Path:
        """
        Permanently store an offline synchronization image.

        Args:
            source_path:
                Temporary uploaded image.

            operation_id:
                Unique synchronization operation ID.

        Returns:
            Path to the permanently stored image.
        """

        if not source_path:
            raise SyncStorageError(
                "Synchronization image path is required."
            )

        source = Path(source_path)

        if not source.exists():
            raise SyncStorageError(
                "Temporary synchronization image was not found."
            )

        if not source.is_file():
            raise SyncStorageError(
                "Temporary synchronization image is not a file."
            )

        if not operation_id:
            raise SyncStorageError(
                "Synchronization operation ID is required."
            )

        storage_directory = cls.get_storage_directory()

        extension = source.suffix.lower()

        destination = (
            storage_directory
            / f"{operation_id}{extension}"
        )

        try:
            shutil.copy2(
                source,
                destination,
            )
        except Exception as exc:
            raise SyncStorageError(
                "Failed to permanently store synchronization image."
            ) from exc

        if not destination.exists():
            raise SyncStorageError(
                "Synchronization image was not stored successfully."
            )

        return destination

    @classmethod
    def delete(cls, image_path: str | Path | None) -> None:
        """
        Delete a permanently stored synchronization image.

        Failure to delete is intentionally ignored because
        cleanup must never invalidate a completed diagnosis.
        """

        if not image_path:
            return

        path = Path(image_path)

        try:
            if path.exists() and path.is_file():
                path.unlink()
        except Exception:
            pass