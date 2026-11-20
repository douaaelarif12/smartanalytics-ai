from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from .config import Settings
from .errors import ApiError
from .analytics import AnalyticsEngine
from .models import AnalyticsQuerySpec, AnalyticsResult, DatasetMetadata, DatasetPreview, DatasetProfile
from .profiling import column_metadata, preview_rows, profile_dataframe, read_dataframe
from .repository import DatasetRepository
from .database import Database
from .profile_cache import PROFILE_VERSION, ProfileCache, ProfileCacheKey


ALLOWED_EXTENSIONS = {".csv": "csv", ".xlsx": "xlsx"}
SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]+")


class DatasetService:
    def __init__(self, settings: Settings, database: Database | None = None):
        self.settings = settings
        self.database = database or Database(settings)
        self.repository = DatasetRepository(settings.data_dir, self.database)
        self.analytics = AnalyticsEngine()
        self.profile_cache = ProfileCache(
            ttl_seconds=settings.profile_cache_ttl_seconds,
            max_entries=settings.profile_cache_max_entries,
            max_bytes=settings.profile_cache_max_bytes,
        )

    @staticmethod
    def validate_id(dataset_id: str) -> str:
        try:
            return str(UUID(dataset_id))
        except ValueError as exc:
            raise ApiError(404, "dataset_not_found",
                           "The requested dataset does not exist.") from exc

    async def create(self, upload: UploadFile, owner_id: str | None = None) -> DatasetMetadata:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        original = Path(upload.filename or "").name
        extension = Path(original).suffix.lower()
        file_type = ALLOWED_EXTENSIONS.get(extension)
        if not original or file_type is None:
            raise ApiError(415, "unsupported_file_type", "Only .csv and .xlsx files are supported.")
        display_name = SAFE_FILENAME.sub("_", original).strip(" ._") or f"dataset{extension}"
        dataset_id = str(uuid4())
        target = self.repository.file_path(dataset_id, file_type)
        size = 0
        created_file = False
        try:
            with target.open("xb") as destination:
                created_file = True
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_upload_bytes:
                        raise ApiError(
                            413, "upload_too_large",
                            f"The file exceeds the configured {self.settings.max_upload_bytes} byte upload limit.",
                            {"max_upload_bytes": self.settings.max_upload_bytes},
                        )
                    destination.write(chunk)
            if size == 0:
                raise ApiError(422, "empty_file", "The uploaded file is empty.")
            frame = read_dataframe(target, file_type)
            columns = column_metadata(frame)
            metadata = DatasetMetadata(
                id=dataset_id,
                name=Path(display_name).stem[:120] or "Untitled dataset",
                original_filename=display_name[:255],
                file_type=file_type,
                file_size_bytes=size,
                row_count=len(frame),
                column_count=len(frame.columns),
                missing_cell_count=int(frame.isna().sum().sum()),
                created_at=datetime.now(UTC),
                columns=columns,
            )
            self.repository.save(metadata, file_type, owner_id)
            return metadata
        except FileExistsError:
            raise ApiError(409, "storage_conflict",
                           "The upload could not allocate new storage. Please retry.") from None
        except Exception:
            if created_file:
                target.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    def list(self, owner_id: str | None = None) -> list[DatasetMetadata]:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        return self.repository.list(owner_id)

    def get(self, dataset_id: str, owner_id: str | None = None) -> DatasetMetadata:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        return self.repository.get(self.validate_id(dataset_id), owner_id)

    def preview(self, dataset_id: str, offset: int, limit: int, owner_id: str | None = None) -> DatasetPreview:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        metadata, path = self.repository.get_path(self.validate_id(dataset_id), owner_id)
        frame = read_dataframe(path, metadata.file_type)
        return DatasetPreview(
            dataset_id=metadata.id, offset=offset, limit=limit, total_rows=len(frame),
            columns=metadata.columns, rows=preview_rows(frame, offset, limit),
        )

    def profile(self, dataset_id: str, owner_id: str | None = None) -> DatasetProfile:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        # Ownership is deliberately resolved before cache access. A cached
        # profile must never turn a cross-tenant request into an existence leak.
        metadata, path = self.repository.get_path(self.validate_id(dataset_id), owner_id)
        identity = path.stat()
        key = ProfileCacheKey(
            owner_id=owner_id,
            dataset_id=metadata.id,
            profile_version=PROFILE_VERSION,
            file_size=identity.st_size,
            file_mtime_ns=identity.st_mtime_ns,
        )
        cached = self.profile_cache.get(key)
        if cached is not None:
            return cached
        profile = profile_dataframe(read_dataframe(path, metadata.file_type), metadata.id)
        self.profile_cache.put(key, profile)
        return profile

    def delete(self, dataset_id: str, owner_id: str | None = None) -> None:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        validated_id = self.validate_id(dataset_id)
        self.repository.delete(validated_id, owner_id)
        self.profile_cache.invalidate(owner_id, validated_id)

    def query(self, dataset_id: str, spec: AnalyticsQuerySpec, owner_id: str | None = None) -> AnalyticsResult:
        if not owner_id:
            raise ApiError(401, "authentication_required", "Please sign in to continue.")
        metadata, path = self.repository.get_path(self.validate_id(dataset_id), owner_id)
        frame = read_dataframe(path, metadata.file_type)
        return self.analytics.execute(frame, metadata.id, metadata.columns, spec)
