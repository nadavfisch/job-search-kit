"""Shared paths and loaders.

Your data lives in a workspace folder, by default my-search/ at the repo root (git-ignored).
Override it with --workspace PATH or the JOBKIT_WORKSPACE environment variable.
"""
import json, os, re, sys
import yaml

KIT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(KIT)


def workspace(arg=None):
    ws = os.path.abspath(arg or os.environ.get("JOBKIT_WORKSPACE") or os.path.join(REPO, "my-search"))
    if not os.path.isdir(ws):
        sys.exit(f"No workspace at {ws}. Run the setup first (SETUP.md).")
    return ws


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_json(path):
    """A batch's jobs_all.json and the like. Missing file = {}."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


# style.css may restyle the CV (colors, fonts, alignment) but not its structure: one text column keeps it ATS-readable.
STYLE_BANNED = [(r"column|grid|display\s*:\s*(inline-)?(flex|table)|float\s*:|(?<![-\w])(position|transform|zoom)\s*:",
                 "side-by-side, positioned or transformed layout (breaks ATS reading order and the page fit)"),
                (r"(^|[},\s])(html|body|\.page)\s*\{[^}]*\bfont(-size)?\s*:", "a font size on html/body/.page (the build sizes the text to fit the page)"),
                (r"gradient\(|image\s*:|url\((?!['\"]?https://fonts\.(googleapis|gstatic)\.com)", "images or gradients (ATS can't read them)"),
                (r"content\s*:", "generated text (ATS may not read it)")]
# Letters spaced .1em apart or more come out of PDF text extraction (pdftotext, pdfminer) as one word per letter.
MAX_LETTER_SPACING = 0.08


def style_problems(css):
    """What a user's style.css may not do, as a list of reasons (empty = fine)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    bad = [why for pat, why in STYLE_BANNED if re.search(pat, css, re.I)]
    for value in re.findall(r"letter-spacing\s*:\s*([^;}]*)", css, re.I):
        m = re.fullmatch(r"(normal|inherit|initial|unset|-?0*\.?0+[a-z%]*|(-?\d*\.?\d+)em)(\s*!important)?", value.strip(), re.I)
        if not m or (m.group(2) and float(m.group(2)) > MAX_LETTER_SPACING):
            bad.append(f"letter-spacing above {MAX_LETTER_SPACING:g}em, or not in em (ATS reads each letter as a word)")
            break
    return bad


def load_profile(ws):
    p = load_yaml(os.path.join(ws, "profile.yaml"))
    for k in ("name", "experience"):
        if not p.get(k):
            sys.exit(f"profile.yaml has no '{k}'.")
    css_path = os.path.join(ws, "style.css")
    if os.path.exists(css_path):
        css = read_text(css_path)
        bad = style_problems(css)
        if bad:
            sys.exit("style.css isn't allowed to use: " + "; ".join(bad))
        p["_css"] = css
    return p


def roles(profile):
    """{role key: role dict}, in profile order (reverse-chronological)."""
    return {r["key"]: r for r in profile["experience"]}


def bullets(profile):
    """{bullet key: (role key, text)} across every role."""
    return {k: (r["key"], t) for r in profile["experience"] for k, t in (r.get("bullets") or {}).items()}


def safe(t):
    return re.sub(r'[/\\:*?"<>|]', "-", str(t)).strip()


# --- tracker.md: one markdown table, one row per job ---
TRACKER_COLS = ["#", "Company", "Role", "Source", "Posted", "Applicants", "Status", "Submitted", "Response", "Follow-up", "Link"]


def tracker_path(ws):
    return os.path.join(ws, "tracker.md")


def cells(line):
    """The cells of one markdown table row."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_cell(value):
    """A value made safe for one markdown table cell."""
    return str(value).replace("|", "/").replace("\n", " ")


def read_tracker(ws):
    """List of row dicts keyed by the header names. Missing file = no rows."""
    path = tracker_path(ws)
    if not os.path.exists(path):
        return []
    lines = [line for line in read_text(path).split("\n") if line.lstrip().startswith("|")]
    if len(lines) < 2:
        return []
    head = cells(lines[0])
    return [dict(zip(head, cells(line))) for line in lines[2:]]


def add_tracker_row(ws, values):
    """Append a row right after the table's last line."""
    path = tracker_path(ws)
    if not os.path.exists(path):
        sys.exit(f"No tracker at {path}: copy templates/tracker.md into the workspace.")
    lines = read_text(path).split("\n")
    rows = [i for i, line in enumerate(lines) if line.lstrip().startswith("|")]
    if not rows:
        sys.exit(f"{path} has no table: copy the header from templates/tracker.md.")
    lines.insert(rows[-1] + 1, "| " + " | ".join(table_cell(values.get(c, "")) for c in TRACKER_COLS) + " |")
    write_text(path, "\n".join(lines))


def append_row(path, row):
    """Append a row to the markdown table at the end of a file (log.md, contacts.md)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write("| " + " | ".join(table_cell(c) for c in row) + " |\n")


def job_dirs(ws):
    """{job number: folder path} for my-search/jobs/NNN - Company - Role/."""
    root = os.path.join(ws, "jobs")
    out = {}
    for name in os.listdir(root) if os.path.isdir(root) else []:
        m = re.match(r"(\d+) - ", name)
        if m and os.path.isdir(os.path.join(root, name)):
            out[int(m.group(1))] = os.path.join(root, name)
    return out


# --- the PDFs in a job folder: "<Name> - <CV title>.pdf" and "<Name> - Cover Letter.pdf" ---
def cv_path(folder, name, title):
    return os.path.join(folder, f"{safe(name)} - {safe(title)}.pdf")


def letter_path(folder, name, ext=".pdf"):
    return os.path.join(folder, f"{safe(name)} - Cover Letter{ext}")


def cv_pdfs(folder, name):
    """Every CV PDF in a folder, whatever its title. Never the cover letter."""
    prefix, letter = f"{safe(name)} - ", os.path.basename(letter_path(folder, name))
    return sorted(os.path.join(folder, f) for f in (os.listdir(folder) if os.path.isdir(folder) else [])
                  if f.startswith(prefix) and f.endswith(".pdf") and f != letter)
