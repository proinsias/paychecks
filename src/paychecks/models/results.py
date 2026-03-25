import enum
from dataclasses import dataclass
from decimal import Decimal


class ValidationStatus(enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


@dataclass(frozen=True)
class FieldResult:
    field_name: str
    expected: Decimal | None
    actual: Decimal | None
    status: ValidationStatus
    note: str | None = None
