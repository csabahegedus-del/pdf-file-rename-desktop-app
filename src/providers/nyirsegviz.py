"""
nyirsegviz.py – parser for Nyírségvíz Zrt. water bills.

Expected output format:
    Nyírségvíz_<invoice> (<period>) víz, <company>.pdf

The company name is looked up from config based on the usage address.
Missing fields are omitted from the generated filename rather than causing errors.
"""
import re
from . import base
from .. import config


class NyirsegvizProvider(base.BaseProvider):
    name = "Nyírségvíz"

    def detect(self, pages: list[str]) -> bool:
        text = "\n".join(pages[:2]) if pages else ""
        return bool(re.search(r"Ny[ií]rs[eé]gv[ií]z", text, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        text = "\n".join(pages[:3])

        invoice = self._invoice_nyirsegviz(text)
        period = self._period_nyirsegviz(text)
        company = self._company(text)

        return {
            "invoice": invoice,
            "period": period,
            "company": company,
            "bill_type": "víz",
        }

    def _invoice_nyirsegviz(self, text: str) -> str | None:
        patterns = [
            r"Sz[aá]mla\s*(?:sorsz[aá]ma|sz[aá]m)[:\s]+(?P<v>[\w\-/]+)",
            r"Sz[aá]mlasz[aá]m[:\s]+(?P<v>[\w\-/]+)",
        ]
        return base._find(patterns, text)

    def _period_nyirsegviz(self, text: str) -> str | None:
        patterns = [
            r"Elsz[aá]mol(?:t|[aá]si)\s+id[oő]szak[:\s]+(?P<v>\d{4}\.\d{2}\.\d{2}\.?\s*[-–]\s*\d{4}\.\d{2}\.\d{2}\.? )",
            r"Teljes[ií]t[eé]si\s+id[oő]szak[:\s]+(?P<v>\d{4}\.\d{2}\.\d{2}\.?\s*[-–]\s*\d{4}\.\d{2}\.\d{2}\.? )",
            r"(?P<v>\d{4}\.\d{2}\.\d{2}\.?\s*[-–]\s*\d{4}\.\d{2}\.\d{2}\.? )",
        ]
        raw = base._find(patterns, text)
        return base.normalise_period(raw) if raw else None

    def _company(self, text: str) -> str | None:
        mapping = config.get("nyirsegviz", "address_company_map") or {}
        lower_text = text.lower()
        for keyword, company in mapping.items():
            if keyword.lower() in lower_text:
                return company
        fallback_company = config.get("nyirsegviz", "default_company")
        return fallback_company or None

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice") or "ISMERETLEN"
        period = parsed.get("period") or ""
        company = parsed.get("company") or ""

        period_part = f" ({period})" if period else ""
        company_part = f", {company}" if company else ""

        return f"Nyírségvíz_{invoice}{period_part} víz{company_part}{ext.lower()}"
