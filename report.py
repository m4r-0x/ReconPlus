"""
ReconPlus - report.py
يبني تقرير HTML مختصر بعد انتهاء الـ run.
بيعتمد على الملفات الفعلية على الديسك (مش أسماء ثابتة بس)، عشان التقرير
ما يطلعش فاضي لو المستخدم شغّل خطوات منفصلة بدون خطوات الدمج (مثلاً subfinder لوحده).

Author : Mohamed Ragab
License: انظر ملف LICENSE
"""
from pathlib import Path
import json
import html
import re

# الملفات "الأساسية" اللي بنفضّلها لو موجودة، والبدايل لو الخطوة الأصلية هي اللي اتشغلت
SUBS_PRIMARY = ["AllSubs.txt"]
SUBS_GLOBS = ["Subs*.txt"]
ALIVE_PRIMARY = ["AliveSubs.txt", "AliveSubs_full.txt"]
URLS_PRIMARY = ["AllURLs.txt"]
URLS_FALLBACK = ["WB1.txt", "GAU1.txt", "GAU2.txt", "KTN1.txt", "HK1.txt", "PS1.txt"]
PORTS_PRIMARY = ["ports.txt"]
SECRETS_PRIMARY = ["secrets_found.txt", "trufflehog_results.json"]
NUCLEI_PRIMARY = ["nuclei_results.txt"]

# ملفات داخلية مالهاش لازمة في الإحصائيات
IGNORED_NAMES = {"report.html", "run_meta.json"}


def _count_lines(p: Path) -> int:
    if not p.exists() or not p.is_file():
        return 0
    return sum(1 for _ in p.open(errors="ignore"))


def _unique_lines(paths) -> int:
    """بيعد الأسطر الفريدة (بدون تكرار) من مجموعة ملفات - نفس منطق خطوة الدمج."""
    seen = set()
    for p in paths:
        p = Path(p)
        if not p.exists() or not p.is_file():
            continue
        for line in p.open(errors="ignore"):
            line = line.strip()
            if line:
                seen.add(line)
    return len(seen)


def _count_from(outdir: Path, primary_names, fallback_globs=(), fallback_names=()) -> int:
    """بيعد من الملف الأساسي لو موجود، وإلا بيجمع ملفات البدايل (بدون تكرار)."""
    for name in primary_names:
        p = outdir / name
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return _count_lines(p)
    fallback_paths = []
    for pattern in fallback_globs:
        fallback_paths.extend(sorted(outdir.glob(pattern)))
    for name in fallback_names:
        fallback_paths.append(outdir / name)
    fallback_paths = [p for p in fallback_paths if p.exists() and p.is_file() and p.stat().st_size > 0]
    if fallback_paths:
        return _unique_lines(fallback_paths)
    return 0


def _category_map() -> dict:
    """{filename: category} من pipeline.json (نفس منطق runner.step_category_map)."""
    pipeline_path = Path(__file__).parent / "pipeline.json"
    try:
        pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    m = {}
    for phase in pipeline.get("phases", []):
        for step in phase.get("steps", []):
            cat = step.get("category", "other")
            for name in re.split(r"[,/]", step.get("produces", "") or ""):
                name = name.strip().split(" ")[0].rstrip("*")
                if name:
                    m[name] = cat
    return m


def _human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _collect_files(outdir: Path):
    """كل ملفات النتائج الفعلية على الديسك مع الفئة والحجم وعدد الأسطر."""
    cat_map = _category_map()
    files = []
    for p in sorted(outdir.rglob("*")):
        if not p.is_file() or p.name in IGNORED_NAMES:
            continue
        rel = str(p.relative_to(outdir)).replace("\\", "/")
        size = p.stat().st_size
        lines = _count_lines(p) if p.suffix.lower() in ("", ".txt", ".csv") else None
        cat = cat_map.get(p.name, cat_map.get(rel, "other"))
        files.append({"rel": rel, "name": p.name, "size": size, "lines": lines, "category": cat})
    files.sort(key=lambda f: (f["category"], f["rel"]))
    return files


def build_report(run) -> str:
    outdir = Path(run["outdir"])
    target = run["target"]

    all_subs = _count_from(outdir, SUBS_PRIMARY, fallback_globs=SUBS_GLOBS)
    alive = _count_from(outdir, ALIVE_PRIMARY)
    all_urls = _count_from(outdir, URLS_PRIMARY, fallback_names=URLS_FALLBACK)
    ports = _count_from(outdir, PORTS_PRIMARY)
    secrets = _count_from(outdir, SECRETS_PRIMARY)
    nuclei = _count_from(outdir, NUCLEI_PRIMARY)

    files = _collect_files(outdir)

    # DEBUG مؤقت - بيتطبع في لوج السيرفر عشان تتأكد من الأرقام والملفات اللي اتقرأت فعلاً
    print(f"[report] run_id={run.get('id')} outdir={outdir}", flush=True)
    print(f"[report] counters: subs={all_subs} alive={alive} urls={all_urls} ports={ports} secrets={secrets} nuclei={nuclei}", flush=True)
    print(f"[report] files on disk: {[f['rel'] for f in files]}", flush=True)

    # جدول بكل الملفات الفعلية على الديسك (يظهر حتى لو الإحصائيات صفر)
    file_rows = ""
    for f in files:
        lines_disp = f["lines"] if f["lines"] is not None else "—"
        file_rows += (
            f"<tr><td>{html.escape(f['rel'])}</td>"
            f"<td>{html.escape(f['category'])}</td>"
            f"<td>{_human_size(f['size'])}</td>"
            f"<td>{lines_disp}</td></tr>"
        )

    # فئات الروابط (لو خطوة التصنيف اتشغلت)
    cat_dir = outdir / "categories"
    cat_rows = ""
    if cat_dir.exists():
        for f in sorted(cat_dir.glob("*.txt")):
            n = _count_lines(f)
            if n:
                cat_rows += f"<tr><td>{html.escape(f.name)}</td><td>{n}</td></tr>"

    done = ", ".join(run.get("done_steps", [])) or "-"
    failed = ", ".join(run.get("failed_steps", [])) or "-"

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
<div class="stat"><b>{len(files)}</b>ملفات النتائج</div>
</div>

<h2>تصنيف الروابط</h2>
<table><tr><th>الفئة</th><th>العدد</th></tr>{cat_rows or '<tr><td colspan=2>لا يوجد</td></tr>'}</table>

<h2>ملفات النتائج على الديسك</h2>
<table><tr><th>الملف</th><th>الفئة</th><th>الحجم</th><th>الأسطر</th></tr>{file_rows or '<tr><td colspan=4>لا يوجد أي ملفات</td></tr>'}</table>

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
