"""
main.py – entry point for the PDF bill rename utility.

Usage:
    python main.py preview    # Parse PDFs, write Excel preview (no file changes)
    python main.py run        # Parse PDFs, copy renamed files to output folder

Both modes write an Excel summary to the 'preview' folder.
"""
import argparse
import logging
import shutil
import sys
from pathlib import Path

# Allow running as "python main.py" from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_reader import PDFReader
from src.providers import detect_provider
from src import excel_exporter
from src.logger_setup import setup_logger


def process(mode: str) -> int:
    base_dir = Path(__file__).parent
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    preview_dir = base_dir / "preview"
    log_dir = base_dir / "log"

    for d in (input_dir, output_dir, preview_dir, log_dir):
        d.mkdir(parents=True, exist_ok=True)

    logger = setup_logger(log_dir)
    logger.info("=== Mode: %s ===", mode.upper())

    pdf_files = sorted(
        [p for p in input_dir.iterdir() if p.suffix.lower() == ".pdf"]
    )

    if not pdf_files:
        logger.warning("No PDF files found in: %s", input_dir)
        print(f"\nNo PDF files found in '{input_dir}'.")
        print("Place your PDF bills in the 'input' folder and try again.")
        return 1

    logger.info("Found %d PDF file(s) in '%s'", len(pdf_files), input_dir)

    results: list[dict] = []

    for pdf_path in pdf_files:
        logger.info("Processing: %s", pdf_path.name)
        result: dict = {
            "original": pdf_path.name,
            "new_name": "",
            "provider": "",
            "invoice": "",
            "period": "",
            "bill_type": "",
            "notes": "",
            "status": "OK",
        }

        try:
            reader = PDFReader(pdf_path)
            pages = reader.extract_text()

            if not pages or not any(pages):
                raise ValueError("No text could be extracted (scanned PDF?)")

            provider = detect_provider(pages)
            if provider is None:
                raise ValueError("Provider not recognised")

            parsed = provider.parse(pages)
            new_name = provider.generate_filename(parsed, pdf_path.suffix)

            result.update(
                {
                    "new_name": new_name,
                    "provider": provider.name,
                    "invoice": parsed.get("invoice", ""),
                    "period": parsed.get("period", ""),
                    "bill_type": parsed.get("bill_type", ""),
                    "notes": parsed.get("notes", "") or "",
                    "status": "OK",
                }
            )

            logger.info("  → %s", new_name)

            if mode == "run":
                dest = output_dir / new_name
                if dest.exists():
                    logger.warning("Destination already exists, skipping: %s", dest.name)
                    result["status"] = "SKIP (already exists)"
                else:
                    shutil.copy2(pdf_path, dest)
                    logger.info("  Copied to output/%s", new_name)

        except Exception as exc:
            logger.error("  FAILED – %s: %s", pdf_path.name, exc)
            result["status"] = f"HIBA: {exc}"

        results.append(result)

    excel_exporter.export(results, preview_dir)

    ok = sum(1 for r in results if r["status"] == "OK")
    failed = len(results) - ok
    logger.info("Done. %d OK, %d failed.", ok, failed)
    print(f"\nFeldolgozva: {ok} OK, {failed} hiba.")
    if mode == "preview":
        print(f"Excel előnézet mentve: {preview_dir}")
    else:
        print(f"Átnevezett fájlok mentve: {output_dir}")
        print(f"Excel összesítő mentve: {preview_dir}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF számla átnevező segédprogram"
    )
    parser.add_argument(
        "mode",
        choices=["preview", "run"],
        help="'preview' = csak Excel összesítő; 'run' = fájlok másolása és átnevezése",
    )
    args = parser.parse_args()
    sys.exit(process(args.mode))


if __name__ == "__main__":
    main()
