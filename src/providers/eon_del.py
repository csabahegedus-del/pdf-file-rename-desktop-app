"""
eon_del.py – parser for E.ON Dél-Dunántúli Áramhálózati Zrt. (electricity) bills.

Expected output format:
    E.ON Dél-Dunántúli (<city>)_<invoice> (<period>) <type>.pdf

Types:
    elszámoló számla → elszámoló
    részszámla       → rész
"""
import re
import logging
from . import base
from .. import config

logger = logging.getLogger("pdf_rename")


class EONDelProvider(base.BaseProvider):
    name = "E.ON Dél-Dunántúli"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(
            re.search(r"E\.ON\s+D[eé]l-Dun[aá]nt[uú]li", first, re.IGNORECASE)
        )

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""
        text = "\n".join(pages[:2])

        invoice = self._invoice(pages)
        period = self._period(pages)
        bill_type = self._bill_type(first)
        city = config.get("eon_del", "city") or self._city(first)

        return {
            "invoice": invoice,
            "period": period,
            "bill_type": bill_type,
            "city": city,
        }

    def _bill_type(self, first_page: str) -> str:
        first_line = first_page.strip().splitlines()[0] if first_page.strip() else ""
        if re.search(r"elsz[aá]mol[oó]", first_line, re.IGNORECASE):
            return "elszámoló"
        if re.search(r"r[eé]szsz[aá]mla", first_line, re.IGNORECASE):
            return "rész"
        return "számla"

    def _city(self, first_page: str) -> str:
        # Try to extract city from provider address line
        m = re.search(r"HU-\d{4}\s+([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüűA-ZÁÉÍÓÖŐÚÜŰ]+)", first_page)
        if m:
            return m.group(1)
        return "Pécs"

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        bill_type = parsed.get("bill_type", "")
        city = parsed.get("city", "Pécs")

        period_part = f" ({period})" if period else ""
        type_part = f" {bill_type}" if bill_type else ""

        return f"E.ON Dél-Dunántúli ({city})_{invoice}{period_part}{type_part}{ext.lower()}"
