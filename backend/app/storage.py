from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .errors import ApiError
from .models import DatasetMetadata


class DatasetRepository:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.files_dir = data_dir / "files"
        self.database_path = data_dir / "metadata.sqlite3"
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    metadata_json TEXT NOT NULL,
                    stored_extension TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def file_path(self, dataset_id: str, extension: str) -> Path:
        return self.files_dir / f"{dataset_id}.{extension}"

    def save(self, metadata: DatasetMetadata, extension: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO datasets(id, metadata_json, stored_extension, created_at) VALUES (?, ?, ?, ?)",
                (metadata.id, metadata.model_dump_json(), extension, metadata.created_at.isoformat()),
            )

    def list(self) -> list[DatasetMetadata]:
        with self._connect() as connection:
            rows = connection.execute("SELECT metadata_json FROM datasets ORDER BY created_at DESC").fetchall()
        return [DatasetMetadata.model_validate_json(row["metadata_json"]) for row in rows]

    def get(self, dataset_id: str) -> DatasetMetadata:
        with self._connect() as connection:
            row = connection.execute("SELECT metadata_json FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if row is None:
            raise ApiError(404, "dataset_not_found", "The requested dataset does not exist.")
        return DatasetMetadata.model_validate_json(row["metadata_json"])

    def get_path(self, dataset_id: str) -> tuple[DatasetMetadata, Path]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT metadata_json, stored_extension FROM datasets WHERE id = ?", (dataset_id,)
            ).fetchone()
        if row is None:
            raise ApiError(404, "dataset_not_found", "The requested dataset does not exist.")
        metadata = DatasetMetadata.model_validate_json(row["metadata_json"])
        path = self.file_path(dataset_id, row["stored_extension"])
        if not path.is_file():
            raise ApiError(500, "dataset_file_missing", "The dataset metadata exists, but its local file is missing.")
        return metadata, path

    def delete(self, dataset_id: str) -> None:
        metadata, path = self.get_path(dataset_id)
        try:
            path.unlink()
        except OSError as exc:
            raise ApiError(500, "dataset_delete_failed", "The local dataset file could not be removed.") from exc
        with self._connect() as connection:
            connection.execute("DELETE FROM datasets WHERE id = ?", (metadata.id,))

