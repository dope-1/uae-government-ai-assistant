from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "dist/huggingface-space"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

MODEL_PREFETCH = (
    'RUN python -c "from sentence_transformers import SentenceTransformer; '
    f"SentenceTransformer('{EMBEDDING_MODEL}')\""
)
UVICORN_CMD = (
    'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", '
    '"--no-access-log", "--no-server-header"]'
)

DOCKERFILE = "\n".join(
    [
        "FROM python:3.12-slim AS runtime",
        "",
        "ENV PYTHONDONTWRITEBYTECODE=1 \\",
        "    PYTHONUNBUFFERED=1 \\",
        "    PIP_NO_CACHE_DIR=1 \\",
        "    HF_HOME=/home/appuser/.cache/huggingface \\",
        "    SENTENCE_TRANSFORMERS_HOME=/home/appuser/.cache/huggingface",
        "",
        "WORKDIR /app",
        "COPY pyproject.toml ./",
        "COPY app ./app",
        'RUN python -m pip install --upgrade pip && python -m pip install ".[ml]"',
        "",
        "RUN useradd --create-home --uid 1000 appuser",
        "USER appuser",
        MODEL_PREFETCH,
        "",
        "EXPOSE 8000",
        UVICORN_CMD,
        "",
    ]
)

README = '''---
title: UAE Government AI Assistant API
emoji: 🇦🇪
colorFrom: red
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# UAE Government AI Assistant API

Backend for an independent bilingual Arabic-English UAE government-information portfolio project.
It is not an official UAE government service and is not affiliated with any UAE government
authority.

The Space expects production secrets/variables for PostgreSQL, Redis, CORS, trusted hosts and the
operations token. See `docs/milestone9_deployment.md` in the main project repository.
'''

DOCKERIGNORE = '''__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
.git/
tests/
alembic/
'''


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    shutil.copy2(BACKEND / "pyproject.toml", OUTPUT / "pyproject.toml")
    shutil.copytree(
        BACKEND / "app",
        OUTPUT / "app",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    (OUTPUT / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
    (OUTPUT / "README.md").write_text(README, encoding="utf-8")
    (OUTPUT / ".dockerignore").write_text(DOCKERIGNORE, encoding="utf-8")

    files = sum(1 for path in OUTPUT.rglob("*") if path.is_file())
    print(f"Wrote standalone Hugging Face Docker Space bundle: {OUTPUT}")
    print(f"Files: {files}")
    print(f"Embedding model baked into the image: {EMBEDDING_MODEL}")


if __name__ == "__main__":
    main()
