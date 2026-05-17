import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
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


def _logo_data_url() -> str:
    logo_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'LOGO.jfif'))
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        return f"data:image/jpeg;base64,{data}"
    return ""


def _make_cover_html(title: str, cover_subtitle: str, subject: str = "", grade: str = "") -> str:
    logo_url = _logo_data_url()
    logo_img = f'<img src="{logo_url}" class="logo" alt="לוגו" />' if logo_url else ""
    subject_display = subject.strip() or title
    grade_display = grade.strip()
    topic_display = title.strip()

    return f"""<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4; margin: 0; }}
        body {{
            margin: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(150deg, #3b1a4a 0%, #7b2d8b 50%, #5c1a7a 100%);
            font-family: Arial, sans-serif;
            color: white;
            text-align: center;
            direction: rtl;
            box-sizing: border-box;
            padding: 40px 60px;
            gap: 0;
        }}
        .logo {{
            width: 110px;
            height: auto;
            border-radius: 14px;
            box-shadow: 0 6px 24px rgba(0,0,0,0.4);
            margin-bottom: 22px;
        }}
        .method-title {{
            font-size: 30px;
            font-weight: 800;
            letter-spacing: 2px;
            margin-bottom: 6px;
            text-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        .method-sub {{
            font-size: 13px;
            opacity: 0.7;
            letter-spacing: 1px;
            margin-bottom: 28px;
        }}
        .divider {{
            width: 50px;
            height: 2px;
            background: rgba(255,255,255,0.4);
            border-radius: 2px;
            margin: 0 auto 28px;
        }}
        .info-block {{
            background: rgba(255,255,255,0.13);
            border: 1px solid rgba(255,255,255,0.25);
            border-radius: 18px;
            padding: 24px 48px;
            margin-bottom: 24px;
            min-width: 300px;
        }}
        .info-row {{
            font-size: 20px;
            font-weight: 700;
            margin: 8px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .info-label {{
            font-weight: 400;
            opacity: 0.75;
            font-size: 16px;
        }}
        .subtitle-badge {{
            background: rgba(255,255,255,0.22);
            border: 1.5px solid rgba(255,255,255,0.5);
            border-radius: 24px;
            padding: 11px 32px;
            font-size: 17px;
            font-weight: 700;
            margin-bottom: 16px;
            letter-spacing: 0.5px;
        }}
        .stations {{
            font-size: 13px;
            opacity: 0.7;
            letter-spacing: 2px;
        }}
    </style></head><body>
    {logo_img}
    <div class="method-title">שיטת א"ל השד"ה</div>
    <div class="method-sub">AL-HASADEH METHOD</div>
    <div class="divider"></div>
    <div class="info-block">
        <div class="info-row"><span class="info-label">שיעור:</span> {subject_display}</div>
        <div class="info-row"><span class="info-label">נושא:</span> {topic_display}</div>
        <div class="info-row"><span class="info-label">כיתה:</span> {grade_display}</div>
    </div>
    <div class="subtitle-badge">{cover_subtitle}</div>
    <div class="stations">הבנה &nbsp;|&nbsp; שיטות &nbsp;|&nbsp; דיוק &nbsp;|&nbsp; אוצר מילים</div>
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


_PROJECT_ROOT = str(Path(__file__).parent.parent)

_MAKE_PDF_SUBPROCESS_SCRIPT = """
import sys, json
sys.path.insert(0, sys.argv[1])
from src.pdf import make_pdf
args = json.loads(sys.stdin.read())
ok = make_pdf(**args)
sys.exit(0 if ok else 1)
"""


def make_pdf_isolated(
    html_files: List[str],
    output_path: str,
    title: str,
    cover_subtitle: str = "",
    subject: str = "",
    grade: str = "",
) -> bool:
    """Run make_pdf in a subprocess to isolate Playwright from the FastAPI async runtime."""
    payload = json.dumps({
        "html_files": html_files,
        "output_path": output_path,
        "title": title,
        "cover_subtitle": cover_subtitle,
        "subject": subject,
        "grade": grade,
    })
    try:
        result = subprocess.run(
            [sys.executable, "-c", _MAKE_PDF_SUBPROCESS_SCRIPT, _PROJECT_ROOT],
            input=payload,
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ},
        )
        if result.returncode != 0:
            log.error(
                "make_pdf_subprocess_failed",
                output_path=output_path,
                returncode=result.returncode,
                stderr=result.stderr[:800],
            )
            return False
        return True
    except subprocess.TimeoutExpired:
        log.error("make_pdf_subprocess_timeout", output_path=output_path, timeout_seconds=180)
        return False
    except Exception as exc:
        log.error("make_pdf_subprocess_error", output_path=output_path, error=str(exc))
        return False


def make_pdf(html_files: List[str], output_path: str, title: str, cover_subtitle: str = "",
             subject: str = "", grade: str = "") -> bool:
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
            _html_to_pdf(page, _make_cover_html(title, cover_subtitle, subject, grade), cover_tmp.name)
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
