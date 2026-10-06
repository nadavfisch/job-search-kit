"""Check and render a job's cover letter (jobs/NNN/cover-letter.md) to PDF, plus a plain .txt for text boxes.

  python3 kit/letter.py <n> [--check] [--force]

cover-letter.md is plain paragraphs separated by blank lines (the greeting and sign-off included), each on one
line. A line break inside a paragraph stays a line break, as in a sign-off ("Best," then the name).
The same truth checks as the CV: every number must be in profile.yaml, and none of the user's banned
patterns may appear. A submitted job's letter isn't re-rendered without --force.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_profile, job_dirs, read_text, write_text, letter_path
from build import new_numbers, source_numbers, frozen
from render import esc, to_pdf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    p = load_profile(ws)
    d = job_dirs(ws).get(a.n)
    src = os.path.join(d or "", "cover-letter.md")
    if not d or not os.path.exists(src):
        sys.exit(f"#{a.n}: no cover-letter.md in the job folder")
    body = read_text(src).strip()
    errors = []
    extra = new_numbers(body, source_numbers(p))
    if extra:
        errors.append(f"numbers not in profile.yaml: {', '.join(extra)}")
    for rule in (p.get("rules") or {}).get("banned") or []:
        if re.search(rule["pattern"], body, re.I):
            errors.append(rule.get("why", "banned pattern " + rule["pattern"]))
    words = len(body.split())
    if words > 400:
        errors.append(f"{words} words: keep it under 400 (250-350 reads best)")
    if errors:
        sys.exit(f"#{a.n} cover letter, nothing rendered:\n  " + "\n  ".join(errors))
    if a.check:
        print(f"OK: {words} words, passes the checks")
        return
    if a.n in frozen(ws) and not a.force:
        sys.exit(f"#{a.n}: already submitted, not re-rendered (--force overwrites it)")

    c = p.get("contact") or {}
    contact = " | ".join(esc(x) for x in (c.get("phone"), c.get("email"), c.get("location")) if x)
    paras = "".join(f"<p>{esc(x.strip())}</p>".replace("\n", "<br>") for x in re.split(r"\n\s*\n", body) if x.strip())
    d_attr = ' dir="rtl"' if p.get("rtl") else ""
    page = (
        f'<!doctype html><html{d_attr}><head><meta charset="utf-8">'
        '<link href="https://fonts.googleapis.com/css2?family=Questrial&family=Roboto:wght@400;700&display=block" rel="stylesheet">'
        "<style>@page{size:A4;margin:0}:root{--text:#333;--name:#444;--contact:#444;--muted:#999;"
        "--font-body:'Roboto',Arial,sans-serif;--font-head:'Questrial','Roboto',Arial,sans-serif;--align-head:left;--case-head:uppercase}"
        "body{margin:0;font-family:var(--font-body);color:var(--text);font-size:10.5pt;line-height:1.5}"
        ".page{padding:18mm 20mm}h1{font-family:var(--font-head);font-weight:400;letter-spacing:.08em;text-align:var(--align-head);"
        "font-size:22pt;color:var(--name);margin:0;text-transform:var(--case-head)}"
        ".contact{font-size:9pt;color:var(--contact);text-align:var(--align-head);margin:4pt 0 18pt}"
        f"p{{margin:0 0 9pt}}</style><style>{p.get('_css', '')}</style>"
        f"<title>{esc(p['name'])} - Cover Letter</title></head><body><div class=page>"
        f"<h1>{esc(p['name'])}</h1><div class=contact>{contact}</div>{paras}</div></body></html>"
    )
    out = letter_path(d, p["name"])
    pages = to_pdf(page, out)
    # Plain-text copy for text boxes: the user never copies from the .md.
    write_text(
        letter_path(d, p["name"], ".txt"),
        "\n\n".join(x.strip() for x in re.split(r"\n\s*\n", body) if x.strip()) + "\n",
    )
    print(out + ("" if pages == 1 else f"  (warning: {pages} pages, shorten it)"))


if __name__ == "__main__":
    main()
