"""
pdf_reader.py – extracts text from every page of a PDF file using pdfplumber.

E2 Hungary bills contain (cid:NNN) ligature escape sequences and garbled
Hungarian characters because of their unusual font encoding.  This module
normalises those sequences so that provider parsers can match clean text.
"""
import re
import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger("pdf_rename")

# Map (cid:NNN) codes found in E2 Hungary PDFs to their correct characters.
_CID_MAP: dict[str, str] = {
    "130": "â",
    "132": "ä",
    "133": "à",
    "135": "ç",
    "137": "ë",
    "138": "è",
    "139": "é",
    "140": "ê",
    "148": "ö",
    "150": "û",
    "151": "ù",
    "154": "ü",
    "158": "ß",
    "160": "á",
    "163": "ú",
    "173": "í",
    "176": "°",
    "185": "±",
    "196": "ä",
    "201": "É",
    "214": "Ö",
    "213": "Ő",
    "215": "×",
    "220": "Ü",
    "225": "á",
    "226": "â",
    "228": "ä",
    "233": "é",
    "237": "í",
    "243": "ó",
    "246": "ö",
    "250": "ú",
    "251": "û",
    "252": "ü",
    "337": "ő",
    "369": "ű",
    "336": "Ő",
    "368": "Ű",
}

# Additional character substitutions for garbled E2 Hungary text.
_CHAR_REPLACEMENTS: list[tuple[str, str]] = [
    ("Æ", "á"),
    ("æ", "á"),
    ("Ø", "é"),
    ("ø", "e"),
    ("œ", "ú"),
    ("Œ", "Ú"),
    ("ı", "i"),
    ("ł", "l"),
    ("Ł", "L"),
]


def _apply_cid(text: str) -> str:
    """Replace (cid:NNN) sequences with the corresponding Unicode character."""
    def _replace(m: re.Match) -> str:
        return _CID_MAP.get(m.group(1), "")
    return re.sub(r"\(cid:(\d+)\)", _replace, text)


def _apply_char_replacements(text: str) -> str:
    for bad, good in _CHAR_REPLACEMENTS:
        text = text.replace(bad, good)
    return text


def normalise(text: str) -> str:
    """Normalise raw PDF text: fix (cid:) codes, special chars, and whitespace."""
    text = _apply_cid(text)
    text = _apply_char_replacements(text)
    # Collapse runs of spaces/tabs while preserving newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Remove leading/trailing whitespace on each line
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines)


class PDFReader:
    """Read and normalise text from each page of a PDF."""

    def __init__(self, path: Path):
        self.path = path

    def extract_text(self) -> list[str]:
        """Return a list of normalised page texts (one entry per page)."""
        pages: list[str] = []
        try:
            with pdfplumber.open(self.path) as pdf:
                for i, page in enumerate(pdf.pages):
                    raw = page.extract_text() or ""
                    pages.append(normalise(raw))
        except Exception as exc:
            logger.error("Failed to read %s: %s", self.path.name, exc)
        return pages
