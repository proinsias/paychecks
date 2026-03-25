from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExtractionError:
    source_file: Path
    field_name: str
    message: str
    page_number: int | None = None
