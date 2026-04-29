"""
elmu.py – parser for ELMŰ Hálózati Kft. (electricity) bills.

Expected output format:
    ELMU_<invoice> (<period>) áram <type> (<last4>) <company>.pdf

The last 4 digits of the "Mérési pont azonosító" field are used to look up
a company name via the mapping in config.json.

Types:
    elszámoló számla → elszámoló
    részszámla       → részszámla[N]   (N = ordinal if present)
"""
import re
import logging
from . import base
from .. import config

logger = logging.getLogger("pdf_rename")


class ELMUProvider(base.BaseProvider):
    name = "ELMŰ"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        return bool(re.search(r"ELM[UŰ]\s+H[aá]l[oó]zati", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        first = pages[0] if pages else ""
        all_text = "\n".join(pages)

        invoice = self._invoice(pages)
        period = self._period(pages)
        bill_type = self._bill_type(first)
        last4, company = self._measurement_point_info(all_text)

        return {
            "invoice": invoice,
            "period": period,
            "bill_type": bill_type,
            "last4": last4,
            "company": company,
        }

    def _bill_type(self, first_page: str) -> str:
        first_line = first_page.strip().splitlines()[0] if first_page.strip() else ""

        # Check for numbered installment: "3. részszámla"
        m = re.search(r"(\d+)\.\s*r[eé]szsz[aá]mla", first_line, re.IGNORECASE)
        if m:
            return f"részszámla{m.group(1)}"

        if re.search(r"elsz[aá]mol[oó]", first_line, re.IGNORECASE):
            return "elszámoló"
        if re.search(r"r[eé]szsz[aá]mla", first_line, re.IGNORECASE):
            return "részszámla"
        return "számla"

    def _measurement_point_info(self, all_text: str) -> tuple[str | None, str | None]:
        """Return (last4, company_name) from Mérési pont azonosító.

        First tries the last 4 digits of the ID; if no mapping is found,
        falls back to the last 4 raw characters of the full ID (e.g. "S---").
        """
        m = re.search(r"M[eé]r[eé]si\s+pont\s+azonos[ií]t[oó][:\s]+(\S+)", all_text, re.IGNORECASE)
        if not m:
            return None, None
        mpid = m.group(1).strip()

        mapping = config.get("elmu", "measurement_point_company_map") or {}

        # Primary: last 4 digits
        digits_only = re.sub(r"\D", "", mpid)
        last4 = digits_only[-4:] if len(digits_only) >= 4 else digits_only
        company = mapping.get(last4)

        # Fallback: last 4 raw characters
        if company is None and len(mpid) >= 4:
            last4 = mpid[-4:]
            company = mapping.get(last4)

        return last4, company

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period = parsed.get("period", "")
        bill_type = parsed.get("bill_type", "")
        last4 = parsed.get("last4")
        company = parsed.get("company")

        period_part = f" ({period})" if period else ""
        company_part = f" ({last4}) {company}" if last4 and company else (f" ({last4})" if last4 else "")

        return f"ELMU_{invoice}{period_part} áram {bill_type}{company_part}{ext.lower()}"
