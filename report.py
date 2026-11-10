"""
ReconPlus - report.py
يبني تقرير HTML مختصر بعد انتهاء الـ run.

Author : Mohamed Ragab
License: انظر ملف LICENSE
"""
from pathlib import Path
import html


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    return sum(1 for _ in p.open(errors="ignore"))


def build_report(run) -> str:
    outdir = Path(run["outdir"])
    target = run["target"]

    all_subs = _count_lines(outdir / "AllSubs.txt")
    alive = _count_lines(outdir / "AliveSubs.txt")
    all_urls = _count_lines(outdir / "AllURLs.txt")
    secrets = _count_lines(outdir / "secrets_found.txt")
    nuclei = _count_lines(outdir / "nuclei_results.txt")
    ports = _count_lines(outdir / "ports.txt")

    cat_dir = outdir / "categories"
    cat_rows = ""
    if cat_dir.exists():
        for f in sorted(cat_dir.glob("*.txt")):
            n = _count_lines(f)
            if n:
                cat_rows += f"<tr><td>{html.escape(f.name)}</td><td>{n}</td></tr>"

    done = ", ".join(run["done_steps"]) or "-"
    failed = ", ".join(run["failed_steps"]) or "-"

    secrets_preview = ""
    secrets_file = outdir / "secrets_found.txt"
    if secrets_file.exists():
        lines = secrets_file.read_text(errors="ignore").splitlines()[:30]
        secrets_preview = "<br>".join(html.escape(l) for l in lines)

    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>تقرير ReconPlus - {html.escape(target)}</title>
<style>
body{{font-family:'Segoe UI',Inter,Tahoma,Arial,sans-serif;background:#1e1e2e;color:#cdd6f4;padding:32px;max-width:900px;margin:auto;line-height:1.6}}
h1{{color:#89b4fa;font-size:24px}}
h2{{color:#89b4fa;font-size:16px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;margin:12px 0}}
td,th{{border:1px solid #313244;padding:9px 12px;text-align:right}}
th{{background:#181825;color:#a6adc8}}
.stat{{display:inline-block;background:#181825;border:1px solid #313244;border-radius:12px;padding:14px 22px;margin:6px;min-width:120px;text-align:center;color:#a6adc8}}
.stat b{{display:block;font-size:22px;color:#b4befe}}
.mono{{font-family:Consolas,monospace;background:#11111b;border:1px solid #313244;padding:12px;border-radius:10px;white-space:pre-wrap;font-size:13px;direction:ltr;text-align:left}}
</style>
</head>
<body>
<h1>تقرير ReconPlus: {html.escape(target)}</h1>
<p>Run ID: {run['id']}</p>

<div>
<div class="stat"><b>{all_subs}</b>Subdomains</div>
<div class="stat"><b>{alive}</b>Alive Hosts</div>
<div class="stat"><b>{all_urls}</b>URLs</div>
<div class="stat"><b>{ports}</b>Ports</div>
<div class="stat"><b>{secrets}</b>Secrets محتملة</div>
<div class="stat"><b>{nuclei}</b>Nuclei Findings</div>
</div>

<h2>تصنيف الروابط</h2>
<table><tr><th>الفئة</th><th>العدد</th></tr>{cat_rows or '<tr><td colspan=2>لا يوجد</td></tr>'}</table>

<h2>Secrets محتملة (أول 30)</h2>
<div class="mono">{secrets_preview or 'لا يوجد'}</div>

<h2>حالة التنفيذ</h2>
<p><b>تمت بنجاح:</b> {html.escape(done)}</p>
<p><b>فشلت/اتخطت:</b> {html.escape(failed)}</p>

<p style="color:#888;font-size:12px">تنبيه: النتائج دي خام وبتحتاج تحقق يدوي قبل أي استخدام (false positives ممكنة خصوصاً في الـ secrets).</p>

<hr style="border-color:#222;margin-top:24px">
<p style="color:#6c7086;font-size:11px;text-align:center">ReconPlus &copy; Mohamed Ragab</p>
</body>
</html>"""
