"""
edv.py – parser for ÉDV Zrt. (water utility) bills.

Expected output format:
    EDV_<invoice> (<period>) <city>, viz.pdf
"""
import re
import logging
from . import base

logger = logging.getLogger("pdf_rename")


class EDVProvider(base.BaseProvider):
    name = "ÉDV"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"[EÉ]DV\s+Zrt\.", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""

        invoice = self._invoice(pages)
        period = self._period(pages)
        city = self._city(first)

        return {
            "invoice": invoice,
            "period": period,
            "city": city,
        }

    def _city(self, first_page: str) -> str | None:
        """Extract city from usage location address."""
        m = re.search(
            r"Felhaszn[aá]l[aá]si\s+hely\s+c[ií]me[:\s]+"
            r".*?\n.*?\n"
            r"([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüűA-ZÁÉÍÓÖŐÚÜŰ]+)",
            first_page, re.IGNORECASE | re.DOTALL,
        )
        if m:
            return m.group(1)
        # Simpler: look for a recognisable city name
        for city in ["Dunaharaszti", "Tatabánya", "Gödöllő", "Budapest", "Eger"]:
            if city.lower() in first_page.lower():
                # Prefer usage location city; check the usage address block
                usage_m = re.search(
                    r"Felhaszn[aá]l[aá]si\s+hely.*?\n(.*?" + re.escape(city) + r".*?)\n",
                    first_page, re.IGNORECASE,
                )
                if usage_m:
                    return city
        # Last resort: return first city found in usage section
        m = re.search(
            r"Felhaszn[aá]l[aá]si\s+hely[^\n]+\n[^\n]*\n([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüűA-ZÁÉÍÓÖŐÚÜŰ ]+)\s",
            first_page, re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        return None

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        city = parsed.get("city") or ""

        period_part = f" ({period})" if period else ""
        city_part = f" {city}," if city else ""

        return f"EDV_{invoice}{period_part}{city_part} viz{ext.lower()}"
