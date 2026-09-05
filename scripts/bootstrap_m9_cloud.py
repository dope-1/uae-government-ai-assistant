from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MANIFEST = ROOT / "data/manifests/official_sources.yaml"
SERVICES = ROOT / "data/services/verified_services.yaml"


def _safe_database_target(database_url: str) -> str:
    sanitized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlsplit(sanitized)
    host = parsed.hostname or "unknown-host"
    database = parsed.path.lstrip("/") or "unknown-database"
    return f"{host}/{database}"


def _run(label: str, args: list[str], *, cwd: Path) -> None:
    print(f"\n== {label} ==")
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit(
            "DATABASE_URL is not set. Set it to the managed PostgreSQL connection string "
            "for the deployment database before running this script."
        )
    lowered = database_url.casefold()
    if "localhost" in lowered or "127.0.0.1" in lowered:
        raise SystemExit(
            "DATABASE_URL points to localhost. Milestone 9 bootstrap is intended for the "
            "managed deployment database."
        )
    for required in (MANIFEST, SERVICES):
        if not required.exists():
            raise SystemExit(f"Required deployment data file is missing: {required}")

    print("Milestone 9 cloud bootstrap")
    print(f"Target database: {_safe_database_target(database_url)}")
    print("Raw credentials are intentionally not printed.")

    _run(
        "Apply Alembic migrations",
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=BACKEND,
    )
    _run(
        "Ingest official-source corpus",
        [sys.executable, str(ROOT / "scripts/ingest.py")],
        cwd=ROOT,
    )
    _run(
        "Seed verified service catalogue",
        [sys.executable, str(ROOT / "scripts/seed_services.py")],
        cwd=ROOT,
    )
    _run("Audit deployed corpus", [sys.executable, str(ROOT / "scripts/audit_corpus.py")], cwd=ROOT)

    print("\nMilestone 9 cloud bootstrap: COMPLETE")


if __name__ == "__main__":
    main()
