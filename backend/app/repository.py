from pathlib import Path
from uuid import UUID
from sqlalchemy import select, delete
from .database import Database
from .db_models import DatasetRecord
from .models import DatasetMetadata
from .errors import ApiError


class DatasetRepository:
    def __init__(self, data_dir: Path, database: Database):
        self.database = database
        self.files_dir = data_dir / "files"
        self.files_dir.mkdir(parents=True, exist_ok=True)

    def file_path(self, dataset_id, extension):
        try:
            identifier = str(UUID(dataset_id))
        except ValueError:
            raise ApiError(404, "dataset_not_found",
                           "The requested dataset does not exist.") from None
        if extension not in {"csv", "xlsx"}:
            raise ApiError(500, "invalid_storage_metadata", "Dataset storage metadata is invalid.")
        path = self.files_dir / f"{identifier}.{extension}"
        if not path.resolve().is_relative_to(self.files_dir.resolve()):
            raise ApiError(404, "dataset_not_found", "The requested dataset does not exist.")
        return path

    def save(self, metadata, extension, owner_id):
        with self.database.session.begin() as session:
            session.add(DatasetRecord(id=metadata.id, owner_id=owner_id, metadata_json=metadata.model_dump_json(
            ), stored_extension=extension, created_at=metadata.created_at.isoformat()))

    def list(self, owner_id):
        with self.database.session() as session:
            records = session.scalars(select(DatasetRecord).where(
                DatasetRecord.owner_id == owner_id).order_by(DatasetRecord.created_at.desc())).all()
            return [DatasetMetadata.model_validate_json(row.metadata_json) for row in records]

    def _record(self, session, dataset_id, owner_id):
        row = session.scalar(select(DatasetRecord).where(DatasetRecord.id ==
                             dataset_id, DatasetRecord.owner_id == owner_id))
        if row is None:
            raise ApiError(404, "dataset_not_found", "The requested dataset does not exist.")
        return row

    def get(self, dataset_id, owner_id):
        with self.database.session() as session:
            return DatasetMetadata.model_validate_json(self._record(session, dataset_id, owner_id).metadata_json)

    def get_path(self, dataset_id, owner_id):
        with self.database.session() as session:
            record = self._record(session, dataset_id, owner_id)
            metadata = DatasetMetadata.model_validate_json(record.metadata_json)
            path = self.file_path(metadata.id, record.stored_extension)
        if not path.is_file():
            raise ApiError(500, "dataset_file_missing", "The dataset file is unavailable.")
        return metadata, path

    def delete(self, dataset_id, owner_id):
        metadata, path = self.get_path(dataset_id, owner_id)
        with self.database.session.begin() as session:
            self._record(session, dataset_id, owner_id)
            # Commit metadata removal only after successful source deletion.
            try:
                path.unlink()
            except OSError:
                raise ApiError(500, "dataset_delete_failed",
                               "The local dataset file could not be removed.") from None
            session.execute(delete(DatasetRecord).where(DatasetRecord.id ==
                            metadata.id, DatasetRecord.owner_id == owner_id))
