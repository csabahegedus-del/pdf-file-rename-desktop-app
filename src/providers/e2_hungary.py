"""
e2_hungary.py – parser for E2 Hungary Zrt. (gas and electricity) bills.

E2 PDFs use a non-standard font encoding that produces garbled text.
The pdf_reader normalisation step resolves most (cid:NNN) codes, but
some characters (Æ→á, Ø→é, œ→ú, ı→i) may still appear.

Expected output format:
    Gas:         E2_<invoice> (<period>) gáz <type>.pdf
    Electricity: E2_<invoice> (<period>) áram <type> (<last4>) <company>.pdf

  period is YYYY.MM (month only) – taken from page 2 "YYYY.MM.havi" billing
  row or from meter start/end dates.

Gas types:
    Teljesítménydíjszámla → kapacitás
    Gáz elszámoló számla  → elszámoló

Electricity types:
    N. Áram részszámla    → reszszamlaN
    Áram részszámla       → reszszamla
    Áram elszámoló számla → elszamolo
"""
import re
import logging
from . import base
from .. import config

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
        utility = self._utility_type(first)

        if utility == "áram":
            bill_type = self._bill_type_electricity(first)
            last4, company = self._measurement_point_info(all_text)
        else:
            bill_type = self._bill_type(first)
            last4, company = None, None

        return {
            "invoice": invoice,
            "period": period,
            "utility": utility,
            "bill_type": bill_type,
            "last4": last4,
            "company": company,
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

    def _utility_type(self, first_page: str) -> str:
        """Return 'áram' for electricity bills, 'gáz' for gas bills."""
        if re.search(r"Villamosenergia|[Áá]ram\s+r[eé]szsz[aá]mla|[Áá]ram\s+elsz[aá]mol|[Áá]ram\s+havi\s+sz[aá]mla", first_page, re.IGNORECASE):
            return "áram"
        return "gáz"

    def _bill_type_electricity(self, first_page: str) -> str:
        """Classify E2 electricity bill type from the first page."""
        first_line = first_page.strip().splitlines()[0] if first_page.strip() else ""

        # Check for numbered installment: "3. Áram részszámla"
        m = re.search(r"(\d+)\.\s*[Áá]ram\s+r[eé]szsz[aá]mla", first_page, re.IGNORECASE)
        if m:
            return f"reszszamla{m.group(1)}"

        if re.search(r"[Áá]ram\s+r[eé]szsz[aá]mla", first_page, re.IGNORECASE):
            return "reszszamla"
        if re.search(r"elsz[aá]mol[oó]", first_page, re.IGNORECASE):
            return "elszamolo"
        return "számla"

    def _measurement_point_info(self, all_text: str) -> tuple[str | None, str | None]:
        """Return (last4_digits, company_name) from Mérési pont azonosító."""
        m = re.search(r"M[eé]r[eé]si\s+pont\s+azonos[ií]t[oó][:\s]+(\S+)", all_text, re.IGNORECASE)
        if not m:
            return None, None
        mpid = m.group(1).strip()
        digits_only = re.sub(r"\D", "", mpid)
        last4 = digits_only[-4:] if len(digits_only) >= 4 else digits_only

        mapping = config.get("e2", "measurement_point_company_map") or {}
        company = mapping.get(last4)
        return last4, company

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
        utility = parsed.get("utility", "gáz")
        last4 = parsed.get("last4")
        company = parsed.get("company")

        period_part = f" ({period})" if period else ""

        if utility == "áram":
            company_part = f" ({last4}) {company}" if last4 and company else (f" ({last4})" if last4 else "")
            return f"E2_{invoice}{period_part} áram {bill_type}{company_part}{ext.lower()}"

        return f"E2_{invoice}{period_part} gáz {bill_type}{ext.lower()}"
