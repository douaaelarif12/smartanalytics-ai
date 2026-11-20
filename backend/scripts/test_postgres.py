"""Run isolation/security tests on a temporary, password-protected PostgreSQL cluster.

Uses an existing PostgreSQL installation. Never connects to or stops the normal local server.
No password or connection URL is printed. No external OpenAI requests are made.
"""
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from sqlalchemy.engine import URL


def main():
    binaries = Path(os.getenv("POSTGRES_BIN_DIR", r"C:\Program Files\PostgreSQL\17\bin"))
    if not all((binaries/name).is_file() for name in ("initdb.exe", "pg_ctl.exe")):
        print("PostgreSQL test binaries unavailable.")
        return 2
    temporary_root = Path(tempfile.gettempdir()).resolve()
    root = Path(tempfile.mkdtemp(prefix="smartanalytics-pg-qa-", dir=temporary_root)).resolve()
    data = root/"cluster"
    password_file = root/"initial-password"
    password = secrets.token_urlsafe(40)
    password_file.write_text(password, encoding="utf-8")
    started = False

    def execute(arguments):
        return subprocess.run([str(item) for item in arguments], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    try:
        initialized = execute([binaries/"initdb.exe", "-D", data, "-U", "qa_admin", "--auth-host=scram-sha-256",
                              "--auth-local=scram-sha-256", "--pwfile", password_file, "--no-locale", "-E", "UTF8"])
        password_file.unlink(missing_ok=True)
        if initialized.returncode:
            print("Temporary PostgreSQL initialization failed; sensitive output suppressed.")
            return 2
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        launched = execute([binaries/"pg_ctl.exe", "-D", data, "-l", root/"server.log", "-o",
                           f"-h 127.0.0.1 -p {port} -c max_connections=40 -c shared_buffers=32MB", "-w", "start"])
        if launched.returncode:
            print("Temporary PostgreSQL start failed; sensitive output suppressed.")
            return 2
        started = True
        url = URL.create("postgresql+psycopg", username="qa_admin", password=password,
                         host="127.0.0.1", port=port, database="postgres")
        environment = {**os.environ,
                       "SMARTANALYTICS_TEST_ADMIN_URL": url.render_as_string(hide_password=False)}
        print("Running security tests against an isolated SCRAM-protected PostgreSQL cluster.", flush=True)
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_security.py", "tests/test_qa.py", "tests/test_saas_http.py",
                                "tests/test_dashboard_migration.py", "tests/test_dashboards.py", "-q",
                                "--tb=short"], cwd=Path(__file__).resolve().parents[1], env=environment, timeout=240)
        return result.returncode
    finally:
        if started:
            stopped = execute([binaries/"pg_ctl.exe", "-D", data, "-m", "fast", "-w", "stop"])
            if stopped.returncode:
                print("Temporary PostgreSQL requires manual cleanup; files retained.")
                raise RuntimeError("Temporary PostgreSQL cleanup was not completed.")
        # Only our own newly created temporary directory is eligible for recursive cleanup.
        if root.parent == temporary_root and root.name.startswith("smartanalytics-pg-qa-"):
            shutil.rmtree(root)


if __name__ == "__main__":
    raise SystemExit(main())
