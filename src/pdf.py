import os
import tempfile
from typing import Any, List

import structlog

from .exceptions import PDFRenderError

log = structlog.get_logger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from pypdf import PdfWriter, PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def save_html(content: str, path: str) -> None:
    """Save HTML content to file. Raises PDFRenderError on failure."""
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.isdir(dir_name):
        try:
            os.makedirs(dir_name, exist_ok=True)
        except OSError as exc:
            log.error("save_html_mkdir_failed", path=path, error=str(exc))
            raise PDFRenderError(
                message=f"Cannot create directory for: {path}",
                detail=str(exc),
            ) from exc
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as exc:
        log.error("save_html_write_failed", path=path, error=str(exc))
        raise PDFRenderError(
            message=f"Failed to write HTML file: {path}",
            detail=str(exc),
        ) from exc
    log.info("html_saved", file=os.path.basename(path))


def _make_cover_html(title: str, cover_subtitle: str) -> str:
    return f"""<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="UTF-8">
    <style>
        @page{{size:A4;margin:0;}}
        body{{margin:0;display:flex;flex-direction:column;justify-content:center;
        align-items:center;height:100vh;
        background:linear-gradient(135deg,#4a235a,#8e44ad);
        font-family:Arial,sans-serif;color:white;text-align:center;direction:rtl;}}
        h1{{font-size:40px;margin-bottom:10px;font-weight:800;}}
        h2{{font-size:24px;font-weight:400;opacity:0.9;margin-bottom:20px;}}
        .badge{{background:rgba(255,255,255,0.2);padding:8px 20px;
        border-radius:16px;font-size:14px;margin:4px;display:inline-block;}}
    </style></head><body>
    <div style="font-size:60px;margin-bottom:16px;">&#128218;</div>
    <h1>א"ל השד"ה</h1>
    <h2>{title}</h2>
    <div class="badge">{cover_subtitle}</div>
    <div class="badge">הבנה | שיטות | דיוק | אוצר מילים</div>
    </body></html>"""


def _html_to_pdf(page: Any, html_content: str, output_path: str) -> None:
    """Render HTML string to PDF using an already-open Playwright page."""
    try:
        page.set_content(html_content, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        page.pdf(
            path=output_path,
            format="A4",
            margin={"top": "1.4cm", "bottom": "1.4cm",
                    "left": "1.6cm", "right": "1.6cm"},
            print_background=True,
        )
    except Exception as exc:
        log.error("html_to_pdf_failed", output_path=output_path, error=str(exc))
        raise PDFRenderError(
            message=f"Playwright PDF rendering failed: {output_path}",
            detail=str(exc),
        ) from exc


def _merge_pdfs(pdf_paths: List[str], output_path: str) -> None:
    writer = PdfWriter()
    for path in pdf_paths:
        if path and os.path.exists(path):
            try:
                reader = PdfReader(path)
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as exc:
                log.error("pdf_read_failed", path=path, error=str(exc))
                continue
    try:
        with open(output_path, "wb") as f:
            writer.write(f)
    except OSError as exc:
        log.error("pdf_merge_write_failed", output_path=output_path, error=str(exc))
        raise PDFRenderError(
            message=f"Failed to write merged PDF: {output_path}",
            detail=str(exc),
        ) from exc


def make_pdf(html_files: List[str], output_path: str, title: str, cover_subtitle: str = "") -> bool:
    if not PDF_AVAILABLE:
        log.warning("pdf_skipped_playwright_missing", hint="pip install playwright && playwright install chromium")
        return False
    if not PYPDF_AVAILABLE:
        log.warning("pdf_skipped_pypdf_missing", hint="pip install pypdf")
        return False

    output_dir = os.path.dirname(output_path) or "."
    tmp_pdfs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Cover page
            cover_tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix="cover_", dir=output_dir, delete=False
            )
            cover_tmp.close()
            _html_to_pdf(page, _make_cover_html(title, cover_subtitle), cover_tmp.name)
            tmp_pdfs.append(cover_tmp.name)

            # Each station HTML → individual PDF
            for i, html_file in enumerate(html_files):
                if not html_file or not os.path.exists(html_file):
                    continue
                with open(html_file, "r", encoding="utf-8") as fh:
                    html_content = fh.read()
                station_tmp = tempfile.NamedTemporaryFile(
                    suffix=".pdf", prefix=f"part{i}_", dir=output_dir, delete=False
                )
                station_tmp.close()
                _html_to_pdf(page, html_content, station_tmp.name)
                tmp_pdfs.append(station_tmp.name)

            browser.close()

        # Merge all individual PDFs
        _merge_pdfs(tmp_pdfs, output_path)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        log.info("pdf_created", file=os.path.basename(output_path), size_mb=round(size_mb, 1))
        return True

    except PDFRenderError:
        raise
    except Exception as e:
        log.error("make_pdf_failed", output_path=output_path, error=str(e))
        return False

    finally:
        for tmp_path in tmp_pdfs:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
