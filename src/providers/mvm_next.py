"""
mvm_next.py – parser for MVM Next Energiakereskedelmi Zrt. (gas) bills.

Expected output format:
    MVM_<invoice> gáz (<period>) <building>_<type> (<ho_label>).<ext>

where:
  building  = "H épület" (extracted from usage location "H ép.")
  type      = "elszámoló" | "részN"
  ho_label  = YYYY.MM.hó  (= month of "Számla kelte" − 1 month)
  ext       = original file extension (may be .PDF or .pdf)
"""
import re
import logging
from calendar import monthrange
from . import base

logger = logging.getLogger("pdf_rename")

# Mapping: building letter → company name (fixed, per business requirement)
_BUILDING_COMPANY: dict[str, str] = {
    "C": "Schuller",
    "E": "Schuller",
    "F": "ODBE",
    "G": "ODBE",
    "H": "ODBE",
}

def _prev_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) of the month before (year, month)."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


class MVMNextProvider(base.BaseProvider):
    name = "MVM Next"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"MVM\s+Next\s+Energiakereskedel", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""
        all_text = "\n".join(pages)

        invoice = self._invoice(pages)
        period = self._period_mvm(pages)
        bill_type = self._bill_type(first)
        building = self._building(all_text)
        ho_label = self._ho_label(all_text)

        return {
            "invoice": invoice,
            "period": period,
            "bill_type": bill_type,
            "building": building,
            "ho_label": ho_label,
        }

    def _period_mvm(self, pages: list[str]) -> str | None:
        """Parse the period; MVM uses trailing dots: '2026.01.05.-2026.02.04.'"""
        text = "\n".join(pages[:2])
        for label in [
            r"Elsz[aá]mol[aá]si id[oő]szak",
            r"Elsz[aá]molt id[oő]szak",
        ]:
            m = re.search(
                label + r"[:\s]+"
                r"(?P<v>\d{4}\.\d{2}\.\d{2}\.?\s*[-–]\s*\.?\d{4}\.\d{2}\.\d{2}\.?)",
                text, re.IGNORECASE,
            )
            if m:
                raw = m.group("v").strip()
                # Normalise to "YYYY.MM.DD.-YYYY.MM.DD." (keep trailing dots for MVM style)
                raw = re.sub(r"(\d{4}\.\d{2}\.\d{2})\.?\s*[-–]\s*\.?(\d{4}\.\d{2}\.\d{2})\.?",
                             r"\1.-\2", raw)
                return raw
        return None

    def _bill_type(self, first_page: str) -> str:
        first_line = first_page.strip().splitlines()[0] if first_page.strip() else ""
        # "11. részszámla" → "rész11"
        m = re.search(r"(\d+)\.\s*r[eé]szsz[aá]mla", first_line, re.IGNORECASE)
        if m:
            return f"rész{m.group(1)}"
        if re.search(r"elsz[aá]mol[oó]", first_line, re.IGNORECASE):
            return "elszámoló"
        if re.search(r"r[eé]szsz[aá]mla", first_line, re.IGNORECASE):
            return "rész"
        return "számla"

    def _building(self, all_text: str) -> str:
        """Extract building identifier from usage location, e.g. 'H ép.' → 'H épület (ODBE)'."""
        m = re.search(r"\b([A-Z])\s+[eé]p\.", all_text)
        if m:
            letter = m.group(1)
            base_name = f"{letter} épület"
            company = _BUILDING_COMPANY.get(letter)
            if company:
                return f"{base_name} ({company})"
            return base_name
        return ""

    def _ho_label(self, all_text: str) -> str | None:
        """
        Find 'Számla kelte: YYYY.MM.DD' and return YYYY.MM of the PREVIOUS month.
        """
        m = re.search(r"Sz[aá]mla\s+kelte[:\s]+(\d{4})\.(\d{2})\.\d{2}", all_text, re.IGNORECASE)
        if m:
            y, mo = _prev_month(int(m.group(1)), int(m.group(2)))
            return f"{y:04d}.{mo:02d}.hó"
        return None

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        bill_type = parsed.get("bill_type", "")
        building = parsed.get("building", "H épület")
        ho_label = parsed.get("ho_label", "")

        period_part = f" ({period})" if period else ""
        building_part = f" {building}" if building else ""
        type_part = f"_{bill_type}" if bill_type else ""
        ho_part = f" ({ho_label})" if ho_label else ""

        return f"MVM_{invoice} gáz{period_part}{building_part}{type_part}{ho_part}{ext}"
