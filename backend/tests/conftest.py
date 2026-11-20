from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.main import create_app
from helpers import sign_in


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    with TestClient(create_app(Settings(cookie_secure=False,data_dir=data_dir, max_upload_bytes=1024 * 1024))) as client:
        sign_in(client)
        yield client

