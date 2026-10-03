"""Pre-submit gate: is every job waiting to be sent ready?

  python3 kit/check_ready.py [n ...]      # default: every tracker row with status apply/stretch and no Submitted date

Per job: the PDF exists, review.md exists and is newer than the PDF, the review verdict isn't ❌,
and the PDF text still matches the current spec.yaml. Exits 1 if anything isn't ready.
Not checked: whether the posting is still open. Look at the job page before submitting.
"""
import argparse, glob, os, re, sys
import pypdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_profile, load_yaml, read_tracker, job_dirs, safe
from build import problems

ap = argparse.ArgumentParser()
ap.add_argument("only", nargs="*", type=int)
ap.add_argument("--workspace")
a = ap.parse_args()
ws = workspace(a.workspace)
p = load_profile(ws)
dirs = job_dirs(ws)
rows = [r for r in read_tracker(ws) if r.get("#", "").isdigit()]
if a.only:
    rows = [r for r in rows if int(r["#"]) in a.only]
else:
    rows = [r for r in rows if not r.get("Submitted") and re.match(r"(apply|stretch)\b", r.get("Status", ""), re.I)]


def flat(t):
    return re.sub(r"\s+", "", t)   # PDF line breaks land anywhere


bad = 0
for r in rows:
    n, issues, verdict = int(r["#"]), [], "?"
    d = dirs.get(n)
    pdfs = glob.glob(os.path.join(d, f"{glob.escape(safe(p['name']))} - *.pdf")) if d else []
    review = os.path.join(d or "", "review.md")
    if not d:
        issues.append("no job folder")
    elif not pdfs:
        issues.append("no PDF (run kit/build.py)")
    elif not os.path.exists(review):
        issues.append("no review.md (run workflows/review.md)")
    else:
        pdf = pdfs[0]
        if os.path.getmtime(review) < os.path.getmtime(pdf):
            issues.append("PDF changed after the review (review again)")
        verdict = next((m.group() for m in re.finditer(r"✅|⚠️|❌", open(review, encoding="utf-8").read())), "?")
        if verdict == "❌":
            issues.append("review verdict ❌")
        errs, spec = problems(p, load_yaml(os.path.join(d, "spec.yaml")))
        if errs:
            issues.append(f"spec.yaml fails the build checks (run kit/build.py --check {n})")
        elif not p.get("rtl"):   # extracted RTL text comes out reordered, so it can't be compared
            text = flat("".join(pg.extract_text() for pg in pypdf.PdfReader(pdf).pages))
            parts = [spec["summary"]] + [t for _, ts in spec["experience"] for t in ts]
            if any(flat(x) not in text for x in parts if x):
                issues.append(f"PDF doesn't match spec.yaml (re-render: kit/build.py {n})")
    bad += bool(issues)
    print(f"#{n} {r.get('Company', '')}: " + ("; ".join(issues) if issues else f"ready (review {verdict})"))
if not rows:
    print("nothing waiting: no apply/stretch rows without a Submitted date")
sys.exit(1 if bad else 0)
