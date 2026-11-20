"""Disposable Compose PostgreSQL + Redis integration suite; no real data or AI calls.

Run from any directory with the backend venv. Never prints service credentials.
Only this invocation's containers/network are stopped. Volumes are always retained.
"""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from uuid import uuid4


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def main():
    root = Path(__file__).resolve().parents[2]
    project = "sa-infra-qa-" + uuid4().hex
    postgres_password, redis_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    postgres_port, redis_port = free_port(), free_port()
    while redis_port == postgres_port:
        redis_port = free_port()
    environment = {**os.environ, "POSTGRES_PASSWORD": postgres_password, "REDIS_PASSWORD": redis_password,
                   "POSTGRES_PORT": str(postgres_port), "REDIS_PORT": str(redis_port)}
    command = ["docker", "compose", "--project-name", project, "--env-file",
               str(root / ".env.compose.example"), "-f", str(root / "compose.yaml")]

    def compose(arguments, timeout=180):
        # CLI errors may contain interpolated URLs: suppress rather than risk logging secrets.
        return subprocess.run(command + arguments, cwd=root, env=environment, timeout=timeout,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode

    try:
        probe = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=15,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode:
            print("Docker engine unavailable; real infrastructure tests NOT executed.")
            return 2
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("Docker engine unavailable or timed out; real infrastructure tests NOT executed.")
        return 2
    try:
        print("Starting isolated PostgreSQL and Redis with health checks.", flush=True)
        if compose(["up", "-d", "--wait", "--wait-timeout", "120", "postgres", "redis"]):
            print("Disposable services failed readiness; integration tests NOT executed.")
            return 2
        environment.update({
            "SMARTANALYTICS_TEST_ADMIN_URL": f"postgresql+psycopg://smartanalytics:{postgres_password}@127.0.0.1:{postgres_port}/postgres",
            "SMARTANALYTICS_TEST_REDIS_URL": f"redis://:{redis_password}@127.0.0.1:{redis_port}/0",
        })
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_security.py",
                                 "tests/test_redis_integration.py", "tests/test_qa.py", "tests/test_saas_http.py",
                                 "tests/test_dashboard_migration.py", "tests/test_dashboards.py",
                                 "-q", "--tb=short"], cwd=root / "backend", env=environment, timeout=600)
        return result.returncode
    finally:
        # Never delete volumes, including those created for this disposable run.
        # The project name is generated here, never supplied by a user/environment.
        if project.startswith("sa-infra-qa-") and len(project) == 44:
            if compose(["down", "--remove-orphans"], timeout=90):
                print("Disposable infrastructure cleanup failed; project retained:", project)
            else:
                print("QA containers stopped; volumes retained for project:", project)


if __name__ == "__main__":
    raise SystemExit(main())
