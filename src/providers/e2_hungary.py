"""
e2_hungary.py – parser for E2 Hungary Zrt. (gas) bills.

E2 PDFs use a non-standard font encoding that produces garbled text.
The pdf_reader normalisation step resolves most (cid:NNN) codes, but
some characters (Æ→á, Ø→é, œ→ú, ı→i) may still appear.

Expected output format:
    E2_<invoice> (<period>) gáz <type>.pdf

  period is YYYY.MM (month only) – taken from page 2 "YYYY.MM.havi" billing
  row or from meter start/end dates.

Types:
    Teljesítménydíjszámla → kapacitás
    Gáz elszámoló számla  → elszámoló
"""
import re
import logging
from . import base

logger = logging.getLogger("pdf_rename")


class E2HungaryProvider(base.BaseProvider):
    name = "E2 Hungary"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"E2\s*Hungary", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""
        all_text = "\n".join(pages)

        invoice = self._invoice_e2(pages)
        period = self._period_e2(pages)
        bill_type = self._bill_type(first)

        return {
            "invoice": invoice,
            "period": period,
            "bill_type": bill_type,
        }

    def _invoice_e2(self, pages: list[str]) -> str | None:
        first = pages[0] if pages else ""
        # Match "Számlaszám: 562003162596" but NOT "Folyószámlaszám:"
        m = re.search(
            r"(?<!Folyó)Sz[aá]mlasz[aá]m[:\s]+(?P<v>\d{9,15})",
            first, re.IGNORECASE,
        )
        if m:
            return m.group("v").strip()
        # Title line: "Teljesítménydíjszámla 562003162596" or "Gáz elszámoló számla 562003254374"
        m = re.search(
            r"(?:Teljes[ií]tm[eé]nyd[ií]jszámla|G[aá]z\s+elsz[aá]mol[oó]\s+sz[aá]mla)\s+(\d{9,15})",
            first, re.IGNORECASE,
        )
        if m:
            return m.group(1)
        return None

    def _period_e2(self, pages: list[str]) -> str | None:
        """Extract YYYY.MM from billing detail table."""
        all_text = "\n".join(pages)
        # "2025.12.havi" in capacity bill detail rows
        m = re.search(r"(\d{4}\.\d{2})\.havi", all_text, re.IGNORECASE)
        if m:
            return m.group(1)
        # Settlement bill: find date range in billing rows "2025.12.01-2025.12.31"
        m = re.search(r"\b(\d{4})\.(\d{2})\.\d{2}-\d{4}\.\d{2}\.\d{2}\b", all_text)
        if m:
            return f"{m.group(1)}.{m.group(2)}"
        # Fallback: consecutive dates in meter table rows "001 2025.12.01 2025.12.31"
        m = re.search(r"\b\d{3}\s+(\d{4})\.(\d{2})\.\d{2}\s+\d{4}\.\d{2}\.\d{2}\b", all_text)
        if m:
            return f"{m.group(1)}.{m.group(2)}"
        # Fallback: "Leolvasás dátuma: YYYY.MM.DD"
        m = re.search(r"Leolvas[aá]sd[aá]tuma[^:]*:(\d{4})\.(\d{2})\.\d{2}", all_text, re.IGNORECASE)
        if m:
            return f"{m.group(1)}.{m.group(2)}"
        # Fallback: "Befizetési határidő: YYYY.MM.DD" → take YYYY.MM
        m = re.search(r"Befizet[eé]si\s*hat[aá]rid[oő][:\s]+(\d{4})\.(\d{2})\.\d{2}", all_text, re.IGNORECASE)
        if m:
            return f"{m.group(1)}.{m.group(2)}"
        return None

    def _bill_type(self, first_page: str) -> str:
        if re.search(r"Teljes[ií]tm[eé]nyd[ií]jszámla", first_page, re.IGNORECASE):
            return "kapacitás"
        if re.search(r"G[aá]z\s+elsz[aá]mol[oó]", first_page, re.IGNORECASE):
            return "elszámoló"
        if re.search(r"elsz[aá]mol[oó]", first_page, re.IGNORECASE):
            return "elszámoló"
        return "számla"

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        bill_type = parsed.get("bill_type", "")

        period_part = f" ({period})" if period else ""

        return f"E2_{invoice}{period_part} gáz {bill_type}{ext.lower()}"
