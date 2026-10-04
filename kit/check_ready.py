"""Pre-submit gate: is every job waiting to be sent ready?

  python3 kit/check_ready.py [n ...]      # default: every tracker row with status apply/stretch and no Submitted date

Per job: the CV PDF for the current spec.yaml title exists, fits max_pages, still matches spec.yaml, and review.md
exists, is newer than the PDF, and its verdict isn't ❌. Exits 1 if anything isn't ready.
Not checked: whether the posting is still open. Look at the job page before submitting.
"""
import argparse, os, re, sys
import pypdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_profile, load_yaml, read_text, read_tracker, job_dirs, cv_path, cv_pdfs
from build import problems

ap = argparse.ArgumentParser()
ap.add_argument("only", nargs="*", type=int)
ap.add_argument("--workspace")
a = ap.parse_args()
ws = workspace(a.workspace)
p = load_profile(ws)
dirs = job_dirs(ws)
rows = [r for r in read_tracker(ws) if r.get("#", "").isdigit()]
missing = sorted(set(a.only) - {int(r["#"]) for r in rows})
if a.only:
    rows = [r for r in rows if int(r["#"]) in a.only]
else:
    rows = [r for r in rows if not r.get("Submitted") and re.match(r"(apply|stretch)\b", r.get("Status", ""), re.I)]


def flat(t):
    return re.sub(r"\s+", "", t)   # PDF line breaks land anywhere


def check(n, d):
    """The reasons job n isn't ready (empty = ready), and the review's verdict."""
    if not d:
        return ["no job folder"], "?"
    if not os.path.exists(os.path.join(d, "spec.yaml")):
        return ["no spec.yaml (workflows/tailor.md)"], "?"
    errs, spec = problems(p, load_yaml(os.path.join(d, "spec.yaml")))
    if errs:
        return [f"spec.yaml fails the build checks (run kit/build.py --check {n})"], "?"
    pdf = cv_path(d, p["name"], spec["title"])
    if not os.path.exists(pdf):
        # a PDF under another title is from an older spec.yaml
        return [f"no PDF{' for the current title' if cv_pdfs(d, p['name']) else ''} (run kit/build.py {n})"], "?"
    issues = []
    reader = pypdf.PdfReader(pdf)
    max_pages = int(p.get("max_pages", 1))
    if len(reader.pages) > max_pages:
        issues.append(f"the PDF has {len(reader.pages)} pages, max_pages is {max_pages} (re-render: kit/build.py {n})")
    if not p.get("rtl"):   # extracted RTL text comes out reordered, so it can't be compared
        text = flat("".join(pg.extract_text() for pg in reader.pages))
        parts = [spec["summary"]] + [t for _, ts in spec["experience"] for t in ts]
        if any(flat(x) not in text for x in parts if x):
            issues.append(f"PDF doesn't match spec.yaml (re-render: kit/build.py {n})")
    review = os.path.join(d, "review.md")
    if not os.path.exists(review):
        return issues + ["no review.md (run workflows/review.md)"], "?"
    if os.path.getmtime(review) < os.path.getmtime(pdf):
        issues.append("PDF changed after the review (review again)")
    # The first verdict sign in review.md is the verdict (its first line, per workflows/review.md).
    # ⚠ is matched with or without the emoji variation selector.
    m = re.search("✅|⚠\ufe0f?|❌", read_text(review))
    verdict = m.group() if m else "?"
    if verdict == "❌":
        issues.append("review verdict ❌")
    return issues, verdict


bad = len(missing)
for n in missing:
    print(f"#{n}: not in tracker.md")
for r in rows:
    n = int(r["#"])
    issues, verdict = check(n, dirs.get(n))
    bad += bool(issues)
    print(f"#{n} {r.get('Company', '')}: " + ("; ".join(issues) if issues else f"ready (review {verdict})"))
if not rows and not a.only:
    print("nothing waiting: no apply/stretch rows without a Submitted date")
sys.exit(1 if bad else 0)
