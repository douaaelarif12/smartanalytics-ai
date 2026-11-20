"""Explicit, repeatable legacy import. No source database or file is modified."""
import argparse
import hashlib
import json
import shutil
import sqlite3
import time
from pathlib import Path
from uuid import UUID, uuid4
from sqlalchemy import select
from .config import Settings
from .database import Database
from .db_models import DatasetRecord, OwnershipDecision, User
from .models import DatasetMetadata
from .repository import DatasetRepository
from .auth import normalize_email


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def import_legacy(database, data_dir, source, owners=None, administrator=None, apply=False):
    source = Path(source).resolve(strict=True)
    owners = owners or {}
    if owners and (not administrator or len(administrator) > 200):
        raise ValueError("An explicit administrator identity is required for ownership decisions.")
    with sqlite3.connect(source.as_uri()+"?mode=ro", uri=True) as legacy:
        legacy.row_factory = sqlite3.Row
        rows = legacy.execute(
            "SELECT id, metadata_json, stored_extension, created_at FROM datasets").fetchall()
    source_ids = {row["id"] for row in rows}
    if set(owners)-source_ids:
        raise ValueError("Ownership mapping contains a dataset absent from the source.")
    repository = DatasetRepository(data_dir, database)
    plans = []
    with database.session.begin() as db:
        for row in rows:
            identifier = str(UUID(row["id"]))
            metadata = DatasetMetadata.model_validate_json(row["metadata_json"])
            extension = row["stored_extension"]
            if metadata.id != identifier or extension not in {"csv", "xlsx"} or metadata.file_type != extension:
                raise ValueError("Legacy metadata is inconsistent; no data was changed.")
            original = source.parent / "files" / f"{identifier}.{extension}"
            if not original.resolve().is_relative_to((source.parent / "files").resolve()) or not original.is_file():
                raise ValueError("A legacy source file is missing or unsafe.")
            target = repository.file_path(identifier, extension)
            if target.exists() and digest(target) != digest(original):
                raise ValueError(
                    "A target file differs from the legacy file; refusing to overwrite it.")
            existing = db.get(DatasetRecord, identifier)
            if existing and (existing.metadata_json != row["metadata_json"] or existing.stored_extension != extension):
                raise ValueError(
                    "Target metadata conflicts with the source; refusing to overwrite it.")
            owner = None
            if identifier in owners:
                owner = db.scalar(select(User).where(
                    User.email == normalize_email(owners[identifier])))
                if owner is None:
                    raise ValueError("An explicitly selected owner account does not exist.")
                if existing and existing.owner_id not in {None, owner.id}:
                    raise ValueError(
                        "An owned dataset cannot be reassigned by the legacy importer.")
            plans.append((row, target, original, existing, owner))
        if apply:
            for row, target, original, existing, owner in plans:
                if target.resolve() != original.resolve() and not target.exists():
                    temporary = target.with_name(target.name+".import-"+uuid4().hex)
                    shutil.copy2(original, temporary)
                    if digest(temporary) != digest(original):
                        raise ValueError("Copied file verification failed.")
                    # No overwrite of an existing target.
                    with target.open("xb") as destination, temporary.open("rb") as copied:
                        shutil.copyfileobj(copied, destination)
                    temporary.unlink()
                if existing is None:
                    existing = DatasetRecord(id=row["id"], owner_id=None, metadata_json=row["metadata_json"],
                                             stored_extension=row["stored_extension"], created_at=row["created_at"])
                    db.add(existing)
                    db.flush()
                if owner and existing.owner_id is None:
                    existing.owner_id = owner.id
                    db.add(OwnershipDecision(id=str(uuid4()), dataset_id=existing.id,
                           owner_id=owner.id, administrator=administrator, created_at=int(time.time())))
    return {"source_datasets": len(plans), "explicit_owner_decisions": len(owners), "applied": apply}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--owners", type=Path,
                        help="JSON object mapping dataset UUIDs to existing account emails")
    parser.add_argument("--administrator",
                        help="Operator identity recorded for explicit ownership decisions")
    parser.add_argument("--apply", action="store_true",
                        help="Without this flag, only validate and report")
    parser.add_argument("--inventory", action="store_true",
                        help="List source IDs/names read-only, without connecting to the target database")
    args = parser.parse_args()
    if args.inventory:
        source = args.source.resolve(strict=True)
        with sqlite3.connect(source.as_uri()+"?mode=ro", uri=True) as legacy:
            rows = legacy.execute("SELECT id, metadata_json FROM datasets ORDER BY id").fetchall()
        print(json.dumps([{"id": row[0], "name": DatasetMetadata.model_validate_json(
            row[1]).name} for row in rows], ensure_ascii=False))
        return
    settings = Settings.from_env()
    database = Database(settings)
    try:
        owners = json.loads(args.owners.read_text(encoding="utf-8")) if args.owners else None
        if owners is not None and (not isinstance(owners, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in owners.items())):
            raise ValueError("Owners must be a JSON object of UUID-to-email strings.")
        print(json.dumps(import_legacy(database, settings.data_dir,
              args.source, owners, args.administrator, args.apply)))
    except (ValueError, FileNotFoundError):
        parser.exit(
            1, "Import validation failed. Check source files, mappings and existing account identities; no overwrite was performed.\n")
    finally:
        database.close()


if __name__ == "__main__":
    main()
