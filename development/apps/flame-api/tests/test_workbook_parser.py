"""Workbook parser limits and acceptance of the owner's final B2 source."""

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.modules.curriculum.workbook_parser import (
    WorkbookRejected, match_key, normalize_text, parse_workbook,
)


def test_normalization_preserves_display_case_and_collapses_whitespace():
    assert normalize_text("  The\tGrand\nCanyon  ") == "The Grand Canyon"
    assert match_key("  SCIENCE  ") == "science"
    assert match_key("Cafe\u0301") == match_key("Café")


def test_parser_rejects_unsafe_or_wrong_files():
    with pytest.raises(WorkbookRejected, match="unsupported_file_type"):
        parse_workbook(b"", filename="curriculum.xls", sheet_levels={"Grade 1": "Grade 1"}, expected_code="fliplecture")
    with pytest.raises(WorkbookRejected, match="invalid_workbook"):
        parse_workbook(b"not a zip", filename="curriculum.xlsx", sheet_levels={"Grade 1": "Grade 1"}, expected_code="fliplecture")
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("xl/workbook.xml", "")
        archive.writestr("xl/externalLinks/externalLink1.xml", "")
    with pytest.raises(WorkbookRejected, match="unsupported_workbook_content"):
        parse_workbook(payload.getvalue(), filename="curriculum.xlsx", sheet_levels={"Grade 1": "Grade 1"}, expected_code="fliplecture")


def test_accepted_final_workbook_when_available():
    path = Path(__file__).resolve().parents[4] / "Curriculum Documents" / "Fliplecture Curriculum Grade 1 to 5.xlsx"
    if not path.exists():
        pytest.skip("Owner workbook is not distributed with the backend package")
    names = ("Grade KG", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5")
    parsed = parse_workbook(path.read_bytes(), filename=path.name,
                            sheet_levels={name: name for name in names}, expected_code="fliplecture")
    assert parsed.valid
    assert sum(parsed.sheet_counts.values()) == 1726
    assert parsed.duplicate_count == 5
    assert len(parsed.rows) == 1726
