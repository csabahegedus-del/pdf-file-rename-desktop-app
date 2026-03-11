"""
dmrv.py – parser for DMRV Zrt. (water utility) bills.

Expected output format:
    DMRV_<invoice> (<period>) <type>[.<notes>].pdf

Types:
    részszámla   → részN  (N = ordinal from "N. részszámla")
    jóváíró      → jóváíró
    elszámoló    → elszamolo
"""
import re
import logging
from . import base
from .. import config

logger = logging.getLogger("pdf_rename")


class DMRVProvider(base.BaseProvider):
    name = "DMRV"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"DMRV\s+Zrt\.", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        text = "\n".join(pages[:2])
        first = pages[0] if pages else ""

        invoice = self._invoice(pages)

        # Period label variants used by DMRV
        period_raw = self._period(
            pages,
            label_variants=[
                r"Elsz[aá]molt id[oő]szak",
                r"Elsz[aá]mol[aá]si id[oő]szak",
            ],
        )

        bill_type = self._bill_type(first)

        notes = None
        if invoice:
            notes_map = config.get("dmrv", "invoice_notes") or {}
            notes = notes_map.get(invoice)

        return {
            "invoice": invoice,
            "period": period_raw,
            "bill_type": bill_type,
            "notes": notes,
        }

    def _bill_type(self, first_page: str) -> str:
        first_line = first_page.strip().splitlines()[0] if first_page.strip() else ""

        # "4. részszámla" → "rész4"
        m = re.search(r"(\d+)\.\s*r[eé]szsz[aá]mla", first_line, re.IGNORECASE)
        if m:
            return f"rész{m.group(1)}"

        if re.search(r"j[oó]v[aá][ií]r[oó]", first_page[:300], re.IGNORECASE):
            return "jóváíró"

        if re.search(r"elsz[aá]mol[oó]", first_page[:300], re.IGNORECASE):
            return "elszamolo"

        if re.search(r"r[eé]szsz[aá]mla", first_page[:300], re.IGNORECASE):
            return "rész"

        return "számla"

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        bill_type = parsed.get("bill_type", "")
        notes = parsed.get("notes")

        period_part = f" ({period})" if period else ""
        type_part = f" {bill_type}" if bill_type else ""
        notes_part = f" ({notes})" if notes else ""

        return f"DMRV_{invoice}{period_part}{type_part}{notes_part}{ext.lower()}"
