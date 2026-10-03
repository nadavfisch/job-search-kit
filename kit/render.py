"""Render a CV spec to a PDF (A4, one page by default) with headless Chrome.

  python3 kit/render.py --check      # is a Chrome / Chromium / Edge binary available?

A spec is what build.py produces from profile.yaml + a job's spec.yaml:
  {"title": str, "summary": str, "experience": [(role key, [bullet text, ...]), ...],
   "skills": [(label, text), ...], "education": bool}
Layout shrinks step by step (font, spacing) until the CV fits in profile["max_pages"] (default 1).
"""
import html, os, shutil, subprocess, sys, tempfile
import pypdf

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome"]


def find_chrome():
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for n in CHROME_NAMES:
        if shutil.which(n):
            return shutil.which(n)
    return None


LABELS = {"experience": "Work Experience", "education": "Education", "skills": "Skills", "languages": "Languages"}

# Letter-spacing stays <= .1em so ATS text extraction reads headings as whole words.
# The look is set by the variables in :root. A user's my-search/style.css (see templates/style.css) can
# override them, and is loaded after this as its own stylesheet.
CSS = """
@page { size: A4; margin: 0; }
:root { --text: #333; --name: #444; --title: #444; --section: #444; --contact: #444; --strong: #3a3a3a; --muted: #999;
        --font-body: 'Roboto', Arial, sans-serif; --font-head: 'Questrial', 'Roboto', Arial, sans-serif;
        --align-head: center; --case-head: uppercase; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; }
body { font-family: var(--font-body); color: var(--text); font-size: @FS@pt; line-height: @LH@; -webkit-print-color-adjust: exact; }
.page { width: 210mm; padding: @TOP@mm 16mm 8mm 16mm; }
/* heading sizes are in em, so they keep their proportion to the body text as the build fits the page */
h1 { font-family: var(--font-head); font-weight: 400; text-align: var(--align-head); letter-spacing: .08em; font-size: 2.4em; line-height: 1.2; color: var(--name); margin: 0; text-transform: var(--case-head); }
.role { font-family: var(--font-head); text-align: var(--align-head); letter-spacing: .08em; font-size: 1.16em; color: var(--title); margin: 4pt 0 10pt; text-transform: var(--case-head); font-weight: 700; }
.contact { text-align: var(--align-head); font-size: .8em; color: var(--contact); margin-bottom: 11pt; }
.contact a { color: inherit; }
.contact .sep, .jh .sep { color: var(--muted); }
.contact .sep { margin: 0 2px; }
.contact .item { white-space: nowrap; }   /* a long contact line wraps between items, never inside one */
.summary { margin: 0 0 @SECT@pt; }
h2 { font-family: var(--font-head); font-weight: 400; letter-spacing: .1em; font-size: 1.39em; color: var(--section); margin: 0 0 5pt; text-transform: var(--case-head); }
.job { margin-bottom: @JOB@pt; }
.jh { font-weight: 700; color: var(--strong); margin-bottom: 2pt; }
ul { margin: 0; padding-inline-start: 16pt; }
li { margin: 0 0 1pt; }
.skills li b { color: var(--strong); }
.sect { margin-bottom: @SECT@pt; }
.plain { margin: 0; }
"""


def esc(t):
    return html.escape(str(t), quote=False)


def build_html(profile, spec, fs, lh, top, sect, job):
    css = (CSS.replace("@FS@", str(fs)).replace("@LH@", str(lh)).replace("@TOP@", str(top))
           .replace("@SECT@", str(sect)).replace("@JOB@", str(job)))
    labels = {**LABELS, **(profile.get("labels") or {})}
    c = profile.get("contact") or {}
    items = []
    if c.get("phone"):
        items.append(f'<a href="tel:{esc(c["phone"]).replace(" ", "")}">{esc(c["phone"])}</a>')
    if c.get("email"):
        items.append(f'<a href="mailto:{esc(c["email"])}">{esc(c["email"])}</a>')
    if c.get("location"):
        items.append(esc(c["location"]))
    items += [f'<a href="{esc(l["url"])}">{esc(l["label"])}</a>' for l in profile.get("links") or []]
    roles = {r["key"]: r for r in profile["experience"]}
    sep = f'<span class="sep"> {esc(profile.get("separator") or "|")} </span>'   # between contact items and header parts

    parts = [f'<div class="page"><h1>{esc(profile["name"])}</h1><div class="role">{esc(spec["title"])}</div>',
             f'<div class="contact">{sep.join(f"<span class=item>{x}</span>" for x in items)}</div>']
    if spec.get("summary"):
        parts.append(f'<div class="summary">{esc(spec["summary"])}</div>')
    parts.append(f'<div class="sect"><h2>{esc(labels["experience"])}</h2>')
    for key, texts in spec["experience"]:
        lis = "".join(f"<li>{esc(t)}</li>" for t in texts)
        # each "|" part isolated, so mixed-direction headers (Hebrew role, English company) keep their order
        header = sep.join(f"<bdi>{esc(x)}</bdi>" for x in roles[key]["header"].split(" | "))
        parts.append(f'<div class="job"><div class="jh">{header}</div>{"<ul>" + lis + "</ul>" if lis else ""}</div>')
    parts.append("</div>")
    if spec.get("education", True) and profile.get("education"):
        lis = "".join(f"<li>{esc(e)}</li>" for e in profile["education"])
        parts.append(f'<div class="sect"><h2>{esc(labels["education"])}</h2><ul class="edu">{lis}</ul></div>')
    if spec.get("skills"):
        lis = "".join(f"<li><b>{esc(l)}:</b> {esc(t)}</li>" for l, t in spec["skills"])
        parts.append(f'<div class="sect"><h2>{esc(labels["skills"])}</h2><ul class="skills">{lis}</ul></div>')
    if profile.get("languages"):
        parts.append(f'<div><h2>{esc(labels["languages"])}</h2><p class="plain">{esc(profile["languages"])}</p></div>')
    parts.append("</div>")
    d = ' dir="rtl"' if profile.get("rtl") else ""
    head = (f'<!doctype html><html{d}><head><meta charset="utf-8">'
            '<link href="https://fonts.googleapis.com/css2?family=Questrial&family=Roboto:wght@400;700&display=block" rel="stylesheet">'
            f'<style>{css}</style><style>{profile.get("_css", "")}</style>'
            f'<title>{esc(profile["name"])} - CV</title></head><body>')
    return head + "".join(parts) + "</body></html>"


def to_pdf(html_text, out):
    chrome = find_chrome()
    if not chrome:
        sys.exit("No Chrome, Chromium or Edge found. Install Google Chrome, or set CHROME_PATH to the browser binary.")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html_text)
        path = f.name
    try:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--virtual-time-budget=8000", f"--print-to-pdf={out}", path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=120)
    finally:
        os.unlink(path)
    return len(pypdf.PdfReader(out).pages)


# (font size, line height, top margin, section gap, job gap), roomiest to tightest.
# Body text stays between 11pt and 9.4pt: inside the usual CV range at both ends.
ROOMY, TIGHT, N = (11.0, 1.45, 14, 13, 8.5), (9.4, 1.3, 8, 6, 4), 17
STEPS = [tuple(round(r + (t - r) * i / (N - 1), 3) for r, t in zip(ROOMY, TIGHT)) for i in range(N)]


def page_fill(pdf):
    """How far down the last page the text reaches, 0-1 (the lowest text line / page height)."""
    page = pypdf.PdfReader(pdf).pages[-1]
    ys = []
    page.extract_text(visitor_text=lambda t, cm, tm, fd, fs: ys.append(tm[5] * cm[3] + cm[5]) if t.strip() else None)
    h = float(page.mediabox.height)
    return round((h - min(ys)) / h, 2) if ys else 0.0


def render(profile, spec, out):
    """Binary-search the roomiest layout step that fits.
    Returns {"step", "pages", "fill"} (fill = how full the last page is), or "OVERFLOW"."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pages = int(profile.get("max_pages", 1))
    lo, hi, best = 0, len(STEPS) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if to_pdf(build_html(profile, spec, *STEPS[mid]), out) <= pages:
            best, hi = mid, mid - 1
        else:
            lo = mid + 1
    if best is None:
        return "OVERFLOW"
    n = to_pdf(build_html(profile, spec, *STEPS[best]), out)
    return {"step": best, "pages": n, "fill": page_fill(out)}


if __name__ == "__main__" and "--check" in sys.argv:
    c = find_chrome()
    sys.exit(print(f"OK: {c}") if c else "No Chrome, Chromium or Edge found. Install Google Chrome, or set CHROME_PATH.")
