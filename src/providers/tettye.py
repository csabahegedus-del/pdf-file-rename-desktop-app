"""
tettye.py – parser for TETTYE FORRÁSHÁZ Zrt. (water utility) bills.

Expected output format:
    Tettye_<invoice> (<period>) reszszamla [viz].pdf
"""
import re
import logging
from . import base

logger = logging.getLogger("pdf_rename")


class TettyeProvider(base.BaseProvider):
    name = "TETTYE"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"TETTYE\s+FORR[AÁ]SH[AÁ]Z", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""

        invoice = self._invoice_tettye(pages)
        period = self._period_tettye(pages)
        bill_type = self._bill_type(first)

        return {
            "invoice": invoice,
            "period": period,
            "bill_type": bill_type,
        }

    def _invoice_tettye(self, pages: list[str]) -> str | None:
        text = "\n".join(pages[:2])
        # Tettye invoice numbers may contain letters: "8364VK26"
        m = re.search(r"Sz[aá]mla\s+sorsz[aá]ma[:\s]+([\w]+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def _period_tettye(self, pages: list[str]) -> str | None:
        text = "\n".join(pages[:2])
        m = re.search(
            r"Elsz[aá]molt\s+id[oő]szak[:\s]+"
            r"(?P<v>\d{4}\.\d{2}\.\d{2}\s*[-–]\s*\d{4}\.\d{2}\.\d{2})",
            text, re.IGNORECASE,
        )
        if m:
            raw = m.group("v").strip()
            return re.sub(r"\s*[-–]\s*", "-", raw)
        return self._period(pages)

    def _bill_type(self, first_page: str) -> str:
        # Tettye uses "N. részszámla" in first line; we show "reszszamla"
        return "reszszamla"

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        bill_type = parsed.get("bill_type", "reszszamla")

        period_part = f" ({period})" if period else ""

        return f"Tettye_{invoice}{period_part} {bill_type} [viz]{ext.lower()}"
