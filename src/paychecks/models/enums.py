import enum

class PayFrequency(enum.Enum):
    WEEKLY = 52
    BIWEEKLY = 26
    SEMIMONTHLY = 24
    MONTHLY = 12

    @property
    def periods_per_year(self) -> int:
        return self.value

class ExtractionMethod(enum.Enum):
    PDFPLUMBER = "pdfplumber"
    OCR = "ocr"
    CLAUDE_CLI = "claude_cli"
