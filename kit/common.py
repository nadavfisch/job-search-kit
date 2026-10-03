"""Shared paths and loaders.

Your data lives in a workspace folder, by default my-search/ at the repo root (git-ignored).
Override it with --workspace PATH or the JOBKIT_WORKSPACE environment variable.
"""
import glob, os, re, sys
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


def load_profile(ws):
    p = load_yaml(os.path.join(ws, "profile.yaml"))
    for k in ("name", "experience"):
        if not p.get(k):
            sys.exit(f"profile.yaml has no '{k}'.")
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


def read_tracker(ws):
    """List of row dicts keyed by the header names. Missing file = no rows."""
    path = tracker_path(ws)
    if not os.path.exists(path):
        return []
    lines = [l for l in open(path, encoding="utf-8") if l.lstrip().startswith("|")]
    if len(lines) < 2:
        return []
    cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    head = cells(lines[0])
    return [dict(zip(head, cells(l))) for l in lines[2:]]


def add_tracker_row(ws, values):
    """Append a row right after the table's last line."""
    path = tracker_path(ws)
    lines = open(path, encoding="utf-8").read().split("\n")
    last = max(i for i, l in enumerate(lines) if l.lstrip().startswith("|"))
    row = "| " + " | ".join(str(values.get(c, "")).replace("|", "/") for c in TRACKER_COLS) + " |"
    lines.insert(last + 1, row)
    open(path, "w", encoding="utf-8").write("\n".join(lines))


def append_row(path, cells):
    """Append a row to the markdown table at the end of a file (log.md, contacts.md)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |\n")


def job_dirs(ws):
    """{job number: folder path} for my-search/jobs/NNN - Company - Role/."""
    out = {}
    for d in glob.glob(os.path.join(ws, "jobs", "*")):
        m = re.match(r"(\d+) - ", os.path.basename(d))
        if m and os.path.isdir(d):
            out[int(m.group(1))] = d
    return out
