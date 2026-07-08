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
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Arial Hebrew', Arial, 'Segoe UI', sans-serif;
            direction: rtl;
            width: 100vw;
            height: 100vh;
            background: linear-gradient(145deg, #22093a 0%, #4a1070 40%, #2d0f5a 70%, #1a0835 100%);
            color: white;
            text-align: center;
            overflow: hidden;
        }}
        /* ── Background layers ── */
        .pattern {{
            position: fixed; inset: 0; z-index: 0;
            opacity: 0.06;
            background-image:
                repeating-linear-gradient(60deg,rgba(255,255,255,.8) 0,rgba(255,255,255,.8) 1px,transparent 0,transparent 50%),
                repeating-linear-gradient(-60deg,rgba(255,255,255,.8) 0,rgba(255,255,255,.8) 1px,transparent 0,transparent 50%);
            background-size: 40px 40px;
        }}
        .top-bar {{
            position: fixed; top: 0; left: 0; right: 0; height: 5mm; z-index: 20;
            background: linear-gradient(90deg, #9b59b6, #6c3483);
        }}
        .bottom-bar {{
            position: fixed; bottom: 0; left: 0; right: 0; height: 5mm; z-index: 20;
            background: linear-gradient(90deg, #6c3483, #9b59b6);
        }}
        /* ── Zone 1: Brand (top 34%) ── */
        .sec-brand {{
            position: fixed; top: 0; left: 0; right: 0;
            height: 34%; z-index: 10;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            padding: 14mm 60px 0;
            gap: 3px;
        }}
        .logo-ring {{
            width: 100px; height: 100px; border-radius: 50%;
            background: rgba(255,255,255,0.1); border: 2px solid rgba(255,255,255,0.28);
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 12px; box-shadow: 0 0 50px rgba(180,100,255,0.35);
        }}
        .logo {{ width: 78px; height: 78px; border-radius: 50%; object-fit: cover;
            border: 2.5px solid rgba(255,255,255,0.45); }}
        .logo-placeholder {{ font-size: 38px; }}
        .method-tag {{ font-size: 9.5px; letter-spacing: 3px; opacity: 0.5; font-weight: 500; }}
        .method-title {{ font-size: 30px; font-weight: 900; letter-spacing: 1px;
            text-shadow: 0 3px 14px rgba(0,0,0,0.4); line-height: 1.1; }}
        .method-sub {{ font-size: 9.5px; letter-spacing: 4px; opacity: 0.4; }}
        .divider {{
            display: flex; align-items: center; gap: 8px;
            width: 200px; margin-top: 10px;
        }}
        .divider-line {{ flex: 1; height: 1px; background: rgba(255,255,255,0.2); }}
        .divider-dot {{ width: 4px; height: 4px; border-radius: 50%; background: rgba(255,255,255,0.4); }}
        /* ── Zone 2: Topic (middle 36%, vertically centered) ── */
        .sec-topic {{
            position: fixed; top: 34%; left: 0; right: 0;
            height: 36%; z-index: 10;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            padding: 0 60px; gap: 14px;
        }}
        .topic-card {{
            background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.22);
            border-radius: 18px; padding: 22px 50px; width: 86%;
        }}
        .topic-label {{ font-size: 9.5px; letter-spacing: 2px; opacity: 0.48; margin-bottom: 6px; }}
        .topic-name {{ font-size: 26px; font-weight: 900; text-shadow: 0 2px 10px rgba(0,0,0,0.3);
            margin-bottom: 14px; line-height: 1.3; }}
        .meta-row {{ display: flex; gap: 20px; justify-content: center; }}
        .meta-item {{ display: flex; flex-direction: column; align-items: center; gap: 2px; }}
        .meta-item-label {{ font-size: 9px; opacity: 0.48; letter-spacing: 1px; }}
        .meta-item-value {{ font-weight: 700; font-size: 14px; }}
        .subtitle-badge {{
            background: linear-gradient(135deg, rgba(155,89,182,0.5), rgba(108,52,131,0.5));
            border: 1.5px solid rgba(255,255,255,0.3); border-radius: 26px;
            padding: 9px 30px; font-size: 14px; font-weight: 700;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }}
        /* ── Zone 3: Bottom cards (bottom 30%) ── */
        .sec-bottom {{
            position: fixed; bottom: 0; left: 0; right: 0;
            height: 30%; z-index: 10;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            padding: 0 50px 12mm; gap: 10px;
        }}
        .station-cards {{
            width: 100%; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
        }}
        .sc {{ border-radius: 10px; padding: 12px 8px; text-align: center; }}
        .sc-red   {{ background: rgba(231,76,60,0.18);  border: 1.5px solid rgba(231,76,60,0.4);  }}
        .sc-blue  {{ background: rgba(52,152,219,0.18); border: 1.5px solid rgba(52,152,219,0.4); }}
        .sc-green {{ background: rgba(46,204,113,0.18); border: 1.5px solid rgba(46,204,113,0.4); }}
        .sc-yellow{{ background: rgba(241,196,15,0.18); border: 1.5px solid rgba(241,196,15,0.4); }}
        .sc-icon {{ font-size: 19px; margin-bottom: 5px; }}
        .sc-name {{ font-size: 12px; font-weight: 800; margin-bottom: 3px; }}
        .sc-desc {{ font-size: 9px; opacity: 0.6; line-height: 1.5; }}
        .copy {{ font-size: 9px; letter-spacing: 2px; opacity: 0.22; }}
    </style></head><body>
    <div class="pattern"></div>
    <div class="top-bar"></div>
    <div class="bottom-bar"></div>

    <div class="sec-brand">
        <div class="logo-ring">
            {'<img src="' + logo_url + '" class="logo" alt="לוגו" />' if logo_url else '<div class="logo-placeholder">📚</div>'}
        </div>
        <div class="method-tag">AL-HASADEH METHOD</div>
        <div class="method-title">שיטת א"ל השד"ה</div>
        <div class="method-sub">COOPERATIVE LEARNING STATIONS</div>
        <div class="divider">
            <div class="divider-line"></div>
            <div class="divider-dot"></div>
            <div class="divider-dot"></div>
            <div class="divider-dot"></div>
            <div class="divider-line"></div>
        </div>
    </div>

    <div class="sec-topic">
        <div class="topic-card">
            <div class="topic-label">נושא הלמידה</div>
            <div class="topic-name">{topic_display}</div>
            <div class="meta-row">
                <div class="meta-item">
                    <span class="meta-item-label">שיעור</span>
                    <span class="meta-item-value">{subject_display}</span>
                </div>
                <div style="width:1px; background:rgba(255,255,255,0.18); height:28px;"></div>
                <div class="meta-item">
                    <span class="meta-item-label">כיתה</span>
                    <span class="meta-item-value">{grade_display}</span>
                </div>
            </div>
        </div>
        <div class="subtitle-badge">{cover_subtitle}</div>
    </div>

    <div class="sec-bottom">
        <div class="station-cards">
            <div class="sc sc-red"><div class="sc-icon">🔴</div><div class="sc-name">הבנה</div><div class="sc-desc">קריאה<br>ודיון בקבוצה</div></div>
            <div class="sc sc-blue"><div class="sc-icon">🔵</div><div class="sc-name">שיטות</div><div class="sc-desc">כתיבה<br>מובנית</div></div>
            <div class="sc sc-green"><div class="sc-icon">🟢</div><div class="sc-name">דיוק</div><div class="sc-desc">לשון<br>ודקדוק</div></div>
            <div class="sc sc-yellow"><div class="sc-icon">🟡</div><div class="sc-name">אוצר מילים</div><div class="sc-desc">משחק<br>ומיון</div></div>
        </div>
        <div class="copy">© כל הזכויות שמורות — שיטת א"ל השד"ה</div>
    </div>

    </body></html>"""


def _html_to_pdf(page: Any, html_content: str, output_path: str) -> None:
    """Render HTML string to PDF using an already-open Playwright page."""
    try:
        page.set_content(html_content, wait_until="domcontentloaded")
        # Inject the fixed-position frame border for station pages.
        # position:fixed repeats on every PDF page in Playwright — this gives
        # a consistent colored border on ALL pages without modifying every renderer.
        if "page-frame-border" not in html_content and "page-header" in html_content:
            page.evaluate(
                "document.body.insertAdjacentHTML('afterbegin',"
                "'<div class=\"page-frame-border\"></div>');"
            )
        page.wait_for_timeout(300)
        page.pdf(
            path=output_path,
            format="A4",
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
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
    }).encode()
    proc = subprocess.Popen(
        [sys.executable, "-c", _MAKE_PDF_SUBPROCESS_SCRIPT, _PROJECT_ROOT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ},
    )
    try:
        stdout, stderr = proc.communicate(input=payload, timeout=180)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()  # drain pipes so the child process fully terminates
        log.error("make_pdf_subprocess_timeout", output_path=output_path, timeout_seconds=180)
        return False
    except Exception as exc:
        proc.kill()
        proc.communicate()
        log.error("make_pdf_subprocess_error", output_path=output_path, error=str(exc))
        return False
    if proc.returncode != 0:
        log.error(
            "make_pdf_subprocess_failed",
            output_path=output_path,
            returncode=proc.returncode,
            stderr=stderr.decode(errors="replace")[:800],
        )
        return False
    return True


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
            # A4 at 96dpi = 794 × 1123 px; correct viewport ensures 100vh == full page
            cover_page = browser.new_page(viewport={"width": 794, "height": 1123})
            page = browser.new_page(viewport={"width": 794, "height": 1123})

            # Cover page
            cover_tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix="cover_", dir=output_dir, delete=False
            )
            cover_tmp.close()
            _html_to_pdf(cover_page, _make_cover_html(title, cover_subtitle, subject, grade), cover_tmp.name)
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

            cover_page.close()
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
