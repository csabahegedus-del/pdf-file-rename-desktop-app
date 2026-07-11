"""
pdf_reader.py – extracts text from every page of a PDF file using pdfplumber.

E2 Hungary bills contain (cid:NNN) ligature escape sequences and garbled
Hungarian characters because of their unusual font encoding.  This module
normalises those sequences so that provider parsers can match clean text.

Some providers (e.g. MVM Émász) issue image-based PDFs whose invoice content
is not extractable as text.  These PDFs may embed the provider name in a
digital signature field and include the structured invoice data as an XML file
attachment.  This module also extracts those sources and appends them to the
first page text so that provider parsers can work without changes.
"""
import re
import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger("pdf_rename")

# Map (cid:NNN) codes found in E2 Hungary PDFs to their correct characters.
_CID_MAP: dict[str, str] = {
    "130": "â",
    "132": "ä",
    "133": "à",
    "135": "ç",
    "137": "ë",
    "138": "è",
    "139": "é",
    "140": "ê",
    "148": "ö",
    "150": "û",
    "151": "ù",
    "154": "ü",
    "158": "ß",
    "160": "á",
    "163": "ú",
    "173": "í",
    "176": "°",
    "185": "±",
    "196": "ä",
    "201": "É",
    "214": "Ö",
    "213": "Ő",
    "215": "×",
    "220": "Ü",
    "225": "á",
    "226": "â",
    "228": "ä",
    "233": "é",
    "237": "í",
    "243": "ó",
    "246": "ö",
    "250": "ú",
    "251": "û",
    "252": "ü",
    "337": "ő",
    "369": "ű",
    "336": "Ő",
    "368": "Ű",
}

# Additional character substitutions for garbled E2 Hungary text.
_CHAR_REPLACEMENTS: list[tuple[str, str]] = [
    ("Æ", "á"),
    ("æ", "á"),
    ("Ø", "é"),
    ("ø", "e"),
    ("œ", "ú"),
    ("Œ", "Ú"),
    ("ı", "i"),
    ("ł", "l"),
    ("Ł", "L"),
]


def _apply_cid(text: str) -> str:
    """Replace (cid:NNN) sequences with the corresponding Unicode character."""
    def _replace(m: re.Match) -> str:
        return _CID_MAP.get(m.group(1), "")
    return re.sub(r"\(cid:(\d+)\)", _replace, text)


def _apply_char_replacements(text: str) -> str:
    for bad, good in _CHAR_REPLACEMENTS:
        text = text.replace(bad, good)
    return text


def normalise(text: str) -> str:
    """Normalise raw PDF text: fix (cid:) codes, special chars, and whitespace."""
    text = _apply_cid(text)
    text = _apply_char_replacements(text)
    # Collapse runs of spaces/tabs while preserving newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Remove leading/trailing whitespace on each line
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines)


def _detect_xml_encoding(xml_bytes: bytes) -> str:
    """Read the encoding declared in an XML header; default to 'iso-8859-2'."""
    header = xml_bytes[:200].decode("ascii", errors="ignore")
    m = re.search(r'encoding=["\']([^"\']+)["\']', header, re.IGNORECASE)
    return m.group(1) if m else "iso-8859-2"


def _parse_xml_attachment(xml_bytes: bytes) -> list[str]:
    """
    Parse an XML invoice attachment and return structured text markers.

    Uses xml.etree.ElementTree so the result is independent of whitespace,
    attribute order, or other formatting details in the XML.  Returns an
    empty list if parsing fails.
    """
    import xml.etree.ElementTree as ET

    encoding = _detect_xml_encoding(xml_bytes)
    try:
        xml_text = xml_bytes.decode(encoding, errors="replace")
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.debug("Could not parse XML attachment: %s", exc)
        return []

    lines: list[str] = []

    # Vendor name ─ helps detection in case signature is absent
    vendor = root.findtext(".//elado/nev") or ""
    if vendor:
        lines.append(f"[XML-elado] {vendor.strip()}")

    # Invoice number (prefer <sorszam>, fall back to szafaz attribute)
    sorszam = root.findtext(".//sorszam")
    if not sorszam:
        szamla = root.find("szamla")
        sorszam = szamla.attrib.get("szafaz") if szamla is not None else None
    if sorszam:
        lines.append(f"[XML-sorszam] {sorszam.strip()}")

    # Billing period: first <tol> element gives the start date
    tol = root.findtext(".//tol")
    if tol:
        lines.append(f"[XML-tol] {tol.strip()}")

    # Invoice type
    tipus = root.findtext(".//szamlatipus")
    if tipus:
        lines.append(f"[XML-szamlatipus] {tipus.strip()}")

    return lines


def _extract_annotations(path: Path) -> str:
    """
    Extract digital-signature signer names and XML file-attachment content
    from PDF AcroForm fields and page annotations.

    MVM Émász invoices are image-based PDFs whose page text contains only the
    recipient address.  The provider name appears in the digital signature's
    /Name field and all structured invoice data (invoice number, period, …) is
    stored in an XML file attached to the PDF.

    Returns a single string that is appended to the first page so that normal
    provider detect/parse methods can match on it.
    """
    extra: list[str] = []
    try:
        # pdfminer is a pdfplumber dependency so it is always available.
        from pdfminer.pdfdocument import PDFDocument  # type: ignore
        from pdfminer.pdfparser import PDFParser  # type: ignore
        from pdfminer.pdftypes import resolve1  # type: ignore

        # Keep file open for the entire duration of object resolution.
        with open(path, "rb") as f:
            parser = PDFParser(f)
            doc = PDFDocument(parser)
            catalog = resolve1(doc.catalog)

            # --- Digital-signature signer names from AcroForm fields ---
            acroform = catalog.get("AcroForm")
            if acroform is not None:
                acroform = resolve1(acroform)
                fields_ref = acroform.get("Fields")
                if fields_ref is not None:
                    for field_ref in resolve1(fields_ref):
                        field = resolve1(field_ref)
                        ft = str(field.get("FT", ""))
                        if ft == "/'Sig'":
                            v_ref = field.get("V")
                            if v_ref is not None:
                                sig = resolve1(v_ref)
                                if hasattr(sig, "get"):
                                    name_val = sig.get(b"Name") or sig.get("Name")
                                    if name_val:
                                        if isinstance(name_val, bytes):
                                            name_val = name_val.decode("latin-1")
                                        extra.append(f"[Aláíró] {name_val}")

            # --- XML file attachments from page annotations ---
            pages_obj = resolve1(catalog.get("Pages", {}))
            kids = pages_obj.get("Kids", [])
            if kids:
                for kid_ref in resolve1(kids):
                    kid = resolve1(kid_ref)
                    annots_ref = kid.get("Annots")
                    if annots_ref is None:
                        continue
                    for ann_ref in resolve1(annots_ref):
                        ann = resolve1(ann_ref)
                        if str(ann.get("Subtype", "")) != "/'FileAttachment'":
                            continue
                        contents = ann.get("Contents", b"")
                        fname = (
                            contents.decode("utf-8", errors="replace")
                            if isinstance(contents, bytes)
                            else str(contents)
                        )
                        if not fname.lower().endswith(".xml"):
                            continue
                        fs = ann.get("FS")
                        if fs is None:
                            continue
                        fs = resolve1(fs)
                        ef = fs.get("EF")
                        if ef is None:
                            continue
                        ef = resolve1(ef) if hasattr(ef, "resolve") else ef
                        f_ref = ef.get("F") or ef.get("UF") if ef else None
                        if f_ref is None:
                            continue
                        stream = resolve1(f_ref)
                        xml_bytes = stream.get_data()
                        extra.extend(_parse_xml_attachment(xml_bytes))

    except Exception as exc:
        logger.debug("Could not extract annotation data from %s: %s", path.name, exc)

    return "\n".join(extra)


class PDFReader:
    """Read and normalise text from each page of a PDF."""

    def __init__(self, path: Path):
        self.path = path

    def extract_text(self) -> list[str]:
        """Return a list of normalised page texts (one entry per page)."""
        pages: list[str] = []
        try:
            with pdfplumber.open(self.path) as pdf:
                for i, page in enumerate(pdf.pages):
                    raw = page.extract_text() or ""
                    pages.append(normalise(raw))
        except Exception as exc:
            logger.error("Failed to read %s: %s", self.path.name, exc)

        # Append digital-signature / XML-attachment data to the first page so
        # that providers can detect and parse image-based PDFs (e.g. MVM Émász).
        # Skip this expensive step for text-based PDFs: if substantial text was
        # already extracted, there is no need to open the file a second time.
        total_text_len = sum(len(p) for p in pages)
        if total_text_len < 200:
            annotation_text = _extract_annotations(self.path)
            if annotation_text:
                if pages:
                    pages[0] = pages[0] + "\n" + annotation_text if pages[0] else annotation_text
                else:
                    pages.append(annotation_text)

        return pages
