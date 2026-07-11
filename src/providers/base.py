"""
base.py – abstract base class for all provider parsers.
"""
import re
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("pdf_rename")


def _find(patterns: list[str], text: str, flags: int = re.IGNORECASE) -> str | None:
    """Try each regex pattern against *text*; return the first named group 'v'."""
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            try:
                return m.group("v").strip()
            except (IndexError, AttributeError):
                pass
    return None


def normalise_period(raw: str) -> str:
    """
    Convert a raw date-range string to 'YYYY.MM.DD-YYYY.MM.DD'.

    Handles:
    - 'YYYY.MM.DD - YYYY.MM.DD'
    - 'YYYY.MM.DD.-YYYY.MM.DD.'   (trailing dots, MVM style)
    - 'YYYY.MM.DD-YYYY.MM.DD'
    """
    # Remove trailing dots from individual date components
    raw = raw.strip()
    # Replace separator variants: ' - ', '.- ', ' -', '.-' → '-'
    raw = re.sub(r"\.?\s*-\s*\.?", "-", raw)
    # Remove any remaining trailing dots
    raw = raw.rstrip(".")
    return raw


class BaseProvider(ABC):
    """All provider parsers must inherit from this class."""

    name: str = "Unknown"

    @abstractmethod
    def detect(self, pages: list[str]) -> bool:
        """Return True if the pages belong to this provider."""

    @abstractmethod
    def parse(self, pages: list[str]) -> dict:
        """
        Parse pages and return a dict with at least:
            invoice, period, bill_type
        May also include: notes, building, company, ho_label, etc.
        """

    @abstractmethod
    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        """Return the full new filename (including extension)."""

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _invoice(self, pages: list[str]) -> str | None:
        return _find(
            [r"[Ss]z[aá]mla\s+sorsz[aá]ma[:\s]+(?P<v>[\w\-]+)"],
            "\n".join(pages[:2]),
        )

    def _period(self, pages: list[str], label_variants: list[str] | None = None) -> str | None:
        labels = label_variants or [
            r"Elsz[aá]mol[aá]si id[oő]szak",
            r"Elsz[aá]molt id[oő]szak",
        ]
        date_re = r"(?P<v>\d{4}\.\d{2}\.\d{2}\.?\s*[-–]\s*\.?\d{4}\.\d{2}\.\d{2}\.?)"
        text = "\n".join(pages[:2])
        for label in labels:
            m = re.search(label + r"[:\s]+" + date_re, text, re.IGNORECASE)
            if m:
                return normalise_period(m.group("v"))
        # Fallback: any date range on the page
        m = re.search(date_re, text)
        if m:
            return normalise_period(m.group("v"))
        return None
