"""Open a job folder and add its tracker row.

From a search batch (description already saved by search.py / fetch_jd.py / add_lead.py):
  python3 kit/new_job.py --batch 2026-10-03 --id 4445001488 --status apply
Any other job (a pasted description: --jd - reads stdin):
  python3 kit/new_job.py --company "Acme" --role "Ops Lead" --link https://... --source manual --jd jd.txt --status apply

Creates my-search/jobs/NNN - Company - Role/ with job-description.txt and an empty spec.yaml,
adds the tracker row, logs "added", and prints the folder path.
"""

import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    workspace,
    job_dirs,
    add_tracker_row,
    read_tracker,
    safe,
    append_row,
    load_json,
    read_text,
    write_text,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch")
    ap.add_argument("--id")
    ap.add_argument("--company")
    ap.add_argument("--role")
    ap.add_argument("--link", default="")
    ap.add_argument(
        "--source", default="manual", help="linkedin / greenhouse / comeet / email-alert / referral / manual ..."
    )
    ap.add_argument("--jd", help="description file, or - for stdin")
    ap.add_argument("--status", default="apply", help="apply / stretch / referral / skip ...")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)

    posted = applicants = ""
    if a.batch and a.id:
        jd_file = os.path.join(ws, "batches", a.batch, "jd", f"{a.id}.txt")
        if not os.path.exists(jd_file):
            sys.exit(
                f"No description at {jd_file}."
                + (f" Run: python3 kit/fetch_jd.py {a.batch} {a.id}" if a.id.isdigit() else "")
            )
        jd = read_text(jd_file)

        def field(k):
            m = re.search(rf"^{k}: (.*)$", jd, re.M)
            return m.group(1).strip() if m else ""

        jobs_file = os.path.join(ws, "batches", a.batch, "jobs_all.json")
        job = load_json(jobs_file).get(a.id, {})
        company, role = (
            a.company or job.get("company") or field("COMPANY"),
            a.role or job.get("title") or field("TITLE"),
        )
        link = job.get("url") or field("URL")
        source = job.get("source") or field("SOURCE") or a.source
        posted, applicants = field("POSTED")[:10], field("APPLICANTS")
    elif a.company and a.role:
        company, role, link, source = a.company, a.role, a.link, a.source
        jd = sys.stdin.read() if a.jd == "-" else (read_text(a.jd) if a.jd else "")
    else:
        sys.exit("Give --batch and --id, or --company and --role.")

    tracked = {
        u.rstrip("/") for r in read_tracker(ws) for u in re.findall(r"https?://[^\s<>()\[\]]+", r.get("Link", ""))
    }
    if link and link.strip().rstrip("/") in tracked:
        sys.exit(f"Already in the tracker: {link}")
    if len(jd.split("---", 1)[-1].strip()) < 200:
        print("warning: the job description is empty or very short. Get the full text before tailoring.")

    n = max(job_dirs(ws), default=0) + 1
    d = os.path.join(ws, "jobs", f"{n:03d} - {safe(company)} - {safe(role)}")
    os.makedirs(d)
    write_text(os.path.join(d, "job-description.txt"), jd)
    write_text(
        os.path.join(d, "spec.yaml"),
        f"# Tailored CV for #{n}. Fill per workflows/tailor.md, then: python3 kit/build.py {n}\n"
        f"company: {json.dumps(company, ensure_ascii=False)}\nrole: {json.dumps(role, ensure_ascii=False)}\n"
        f"link: {json.dumps(link, ensure_ascii=False)}\n"
        "title:            # close to the posting's title, never a level you don't hold\n"
        "summary: >\n  \n"
        "experience:       # role keys from profile.yaml; order doesn't matter, it renders reverse-chronologically\n"
        "  # - role: <role key>\n  #   bullets:\n  #     - <bullet key>\n"
        '  #     - from: <bullet key>\n  #       text: "<same facts, the job\'s words>"\n'
        "skills:           # skills keys from profile.yaml, or {label: ..., text: ...}\n",
    )
    add_tracker_row(
        ws,
        {
            "#": n,
            "Company": company,
            "Role": role,
            "Source": source,
            "Posted": posted,
            "Applicants": applicants,
            "Status": a.status,
            "Link": link,
        },
    )
    log = os.path.join(ws, "log.md")
    if os.path.exists(log):
        append_row(
            log,
            [datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), n, company, "added", f"{role} ({source}, {a.status})"],
        )
    print(d)


if __name__ == "__main__":
    main()
