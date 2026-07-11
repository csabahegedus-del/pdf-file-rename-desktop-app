"""
mvm_emasz.py – parser for MVM Émász Áramhálózati Kft. (electricity grid) bills.

Expected output format:
    MVM Émász_<invoice> (<YYYY.MM>) áram hálózat, Eger.<ext>

where:
  invoice  = "Számla sorszáma" value (e.g. 752503136176)
  YYYY.MM  = year and month extracted from "Elszámolási időszak" start date

MVM Émász invoices are image-based PDFs.  The provider name appears in the
digital signature field (injected as "[Aláíró] MVM Émász …" by pdf_reader)
and the structured invoice data is in an embedded XML attachment
(injected as "[XML:…]" by pdf_reader).
"""
import re
import logging
from . import base

logger = logging.getLogger("pdf_rename")


class MVMEmaszProvider(base.BaseProvider):
    name = "MVM Émász"

    def detect(self, pages: list[str]) -> bool:
        first = pages[0] if pages else ""
        # Primary: match the digital-signature signer name injected by pdf_reader
        if re.search(r"\[Aláíró\].*MVM\s+[EÉ]m[aá]sz", first, re.IGNORECASE):
            return True
        # Fallback: match plain text in text-based PDFs
        return bool(re.search(r"MVM\s+[EÉ]m[aá]sz\s+[AÁ]ramh[aá]l[oó]zati", first, re.IGNORECASE))

    def parse(self, pages: list[str]) -> dict:
        all_text = "\n".join(pages)

        # Try structured-marker extraction first (image-based PDFs with embedded XML)
        invoice = self._invoice_from_marker(all_text) or self._invoice_emasz(all_text)
        period_ym = self._period_ym_from_marker(all_text) or self._period_ym(all_text)

        return {
            "invoice": invoice,
            "period_ym": period_ym,
        }

    # ------------------------------------------------------------------
    # Structured-marker helpers (injected by pdf_reader from XML attachment)
    # ------------------------------------------------------------------

    def _invoice_from_marker(self, text: str) -> str | None:
        """Extract invoice number from '[XML-sorszam] <value>' marker."""
        m = re.search(r"^\[XML-sorszam\]\s*(\S+)", text, re.MULTILINE)
        return m.group(1) if m else None

    def _period_ym_from_marker(self, text: str) -> str | None:
        """
        Extract YYYY.MM from '[XML-tol] YYYY.MM.DD-…' marker.
        E.g. '[XML-tol] 2026.01.01-2026.01.31'  →  '2026.01'
        """
        m = re.search(r"^\[XML-tol\]\s*(\d{4})\.(\d{2})\.\d{2}", text, re.MULTILINE)
        return f"{m.group(1)}.{m.group(2)}" if m else None

    # ------------------------------------------------------------------
    # Text-based helpers (text-based PDF fallback)
    # ------------------------------------------------------------------

    def _invoice_emasz(self, text: str) -> str | None:
        """Extract invoice number from 'Számla sorszáma: 752503136176'."""
        m = re.search(r"Sz[aá]mla\s+sorsz[aá]ma[:\s]+(\d+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def _period_ym(self, text: str) -> str | None:
        """
        Extract YYYY.MM from 'Elszámolási időszak: 2026.01.01-2026.01.31'.
        Returns only the year and month of the start date.
        """
        m = re.search(
            r"Elsz[aá]mol[aá]si\s+id[oő]szak[:\s]*(\d{4})\.(\d{2})\.\d{2}",
            text,
            re.IGNORECASE,
        )
        if m:
            return f"{m.group(1)}.{m.group(2)}"
        return None

    def generate_filename(self, parsed: dict, ext: str = ".pdf") -> str:
        invoice = parsed.get("invoice", "ISMERETLEN")
        period_ym = parsed.get("period_ym", "")

        period_part = f" ({period_ym})" if period_ym else ""

        return f"MVM Émász_{invoice}{period_part} áram hálózat, Eger{ext.lower()}"
