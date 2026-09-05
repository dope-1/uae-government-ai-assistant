from pathlib import Path

import yaml
from pydantic import TypeAdapter

from app.ingestion.schemas import SourceSpec


def load_manifest(path: Path) -> list[SourceSpec]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return TypeAdapter(list[SourceSpec]).validate_python(data.get("sources", []))
