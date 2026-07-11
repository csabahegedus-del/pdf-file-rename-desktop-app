"""
heves_megyei.py – parser for Heves Megyei Vízmű Zrt. bills.

Expected output format:
    Heves Megyei Vizmu_<invoice> (<period>) <company> (<ho_label>).pdf

where:
  invoice   = document number, e.g. "2026-00-10019011"
  period    = "YYYY.MM.DD - YYYY.MM.DD" (spaces around dash, as on the bill)
  company   = looked up from config based on usage address keyword
  ho_label  = "YYYY.MM.havi" – YYYY.MM = start month of the billing period
"""
import re
import logging
from . import base
from .. import config

logger = logging.getLogger("pdf_rename")


class HevesMegyeiProvider(base.BaseProvider):
    name = "Heves Megyei Vízmű"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"Heves\s+Megyei\s+V[ií]zm[uű]", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""

        invoice = self._invoice_hm(pages)
        period_raw = self._period_hm(pages)
        company = self._company(first)
        ho_label = self._ho_label(period_raw)

        return {
            "invoice": invoice,
            "period": period_raw,
            "bill_type": "elszámoló",
            "company": company,
            "ho_label": ho_label,
        }

    def _invoice_hm(self, pages: list[str]) -> str | None:
        text = "\n".join(pages[:2])
        # Format: "2026-00-10019011"
        m = re.search(r"Sz[aá]mla\s+sorsz[aá]ma[:\s]+(\d{4}-\d{2}-\d{10,12})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return self._invoice(pages)

    def _period_hm(self, pages: list[str]) -> str | None:
        text = "\n".join(pages[:2])
        # Keep spaces around the dash as they appear in the original
        m = re.search(
            r"Elsz[aá]mol[aá]si\s+id[oő]szak[:\s]+"
            r"(?P<v>\d{4}\.\d{2}\.\d{2}[-– ]+\d{4}\.\d{2}\.\d{2})",
            text, re.IGNORECASE,
        )
        if m:
            raw = m.group("v").strip()
            # Normalise to "YYYY.MM.DD-YYYY.MM.DD" then add spaces for Heves style
            raw = re.sub(r"\s*[-–]\s*", " - ", raw)
            return raw
        return None

    def _company(self, first_page: str) -> str | None:
        mapping = config.get("heves_megyei", "address_company_map") or {}
        for keyword, company in mapping.items():
            if keyword.lower() in first_page.lower():
                return company
        return None

    def _ho_label(self, period: str | None) -> str | None:
        if not period:
            return None
        m = re.match(r"(\d{4})\.(\d{2})\.\d{2}", period)
        if m:
            return f"{m.group(1)}.{m.group(2)}.havi"
        return None

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        company = parsed.get("company") or ""
        ho_label = parsed.get("ho_label") or ""

        period_part = f" ({period})" if period else ""
        company_part = f" {company}" if company else ""
        ho_part = f" ({ho_label})" if ho_label else ""

        return f"Heves Megyei Vizmu_{invoice}{period_part}{company_part}{ho_part}{ext.lower()}"
