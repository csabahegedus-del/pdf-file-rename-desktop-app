"""
fovarosi_vizmuvek.py – parser for Fővárosi Vízművek Zrt. bills.

Expected output format:
    Fovarosi Vizmuvek_<invoice> (<period>) <part>.rész <company>, viz.pdf

where <part> is the ordinal from "N. részszámla" in the first line.
The company name is looked up from config based on the usage address.
"""
import re
import logging
from . import base
from .. import config

logger = logging.getLogger("pdf_rename")


class FovarosiVizmuvekProvider(base.BaseProvider):
    name = "Fővárosi Vízművek"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"F[oő]v[aá]rosi\s+V[ií]zm[uű]vek", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""

        invoice = self._invoice_fvm(pages)
        period = self._period_fvm(pages)
        part_num = self._part_number(first)
        company = self._company(first)

        return {
            "invoice": invoice,
            "period": period,
            "part_num": part_num,
            "company": company,
        }

    def _invoice_fvm(self, pages: list[str]) -> str | None:
        """Fővárosi Vízművek uses 'Számlaszám' (not 'Számla sorszáma')."""
        text = "\n".join(pages[:2])
        m = re.search(r"Sz[aá]mlasz[aá]m[:\s]+(?P<v>\d{10,15})", text, re.IGNORECASE)
        if m:
            return m.group("v").strip()
        return self._invoice(pages)

    def _period_fvm(self, pages: list[str]) -> str | None:
        text = "\n".join(pages[:2])
        m = re.search(
            r"Elsz[aá]molt\s+id[oő]szak[:\s]+"
            r"(?P<v>\d{4}\.\d{2}\.\d{2}\s*[-–]\s*\d{4}\.\d{2}\.\d{2}\.?)",
            text, re.IGNORECASE,
        )
        if m:
            raw = m.group("v").strip().rstrip(".")
            return re.sub(r"\s*[-–]\s*", "-", raw)
        return self._period(pages)

    def _part_number(self, first_page: str) -> str | None:
        m = re.search(r"(\d+)\.\s*r[eé]szsz[aá]mla", first_page, re.IGNORECASE)
        if m:
            return m.group(1)
        return None

    def _company(self, first_page: str) -> str | None:
        mapping = config.get("fovarosi_vizmuvek", "address_company_map") or {}
        for keyword, company in mapping.items():
            if keyword.lower() in first_page.lower():
                return company
        return None

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        part_num = parsed.get("part_num")
        company = parsed.get("company") or ""

        period_part = f" ({period})" if period else ""
        part_part = f" {part_num}.rész" if part_num else ""
        company_part = f" {company}," if company else ""

        return f"Fovarosi Vizmuvek_{invoice}{period_part}{part_part}{company_part} viz{ext.lower()}"
