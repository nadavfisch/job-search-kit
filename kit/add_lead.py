"""Add a job lead from anywhere (an email alert, a friend, a job site) to a search batch, so it gets triaged
with the rest.

  python3 kit/add_lead.py --batch 2026-10-03 --source alljobs --company "Acme" --title "Ops Lead" \
      --link https://... [--location "Tel Aviv"] [--posted 2026-10-01] [--jd -]      # --jd - reads the description from stdin

Prints the lead's id (for new_job.py --batch <date> --id <id>). Without --jd, open the link and add the
description before triage: a lead is never triaged on its title alone.
"""
import argparse, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace

ap = argparse.ArgumentParser()
ap.add_argument("--batch", required=True); ap.add_argument("--source", required=True)
ap.add_argument("--company", required=True); ap.add_argument("--title", required=True); ap.add_argument("--link", required=True)
ap.add_argument("--location", default=""); ap.add_argument("--posted", default=""); ap.add_argument("--jd")
ap.add_argument("--workspace")
a = ap.parse_args()
ws = workspace(a.workspace)
out = os.path.join(ws, "batches", a.batch)
os.makedirs(os.path.join(out, "jd"), exist_ok=True)
jobs_file = os.path.join(out, "jobs_all.json")
jobs = json.load(open(jobs_file, encoding="utf-8")) if os.path.exists(jobs_file) else {}
jid = "lead-" + hashlib.sha1(a.link.encode()).hexdigest()[:10]
if jid in jobs:
    sys.exit(f"{jid}: already in batch {a.batch}")
jobs[jid] = dict(id=jid, title=a.title, company=a.company, location=a.location, date=a.posted, url=a.link, source=a.source, new=True, q=[])
json.dump(jobs, open(jobs_file, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if a.jd:
    desc = sys.stdin.read() if a.jd == "-" else open(a.jd, encoding="utf-8").read()
    hdr = (f"ID: {jid}\nTITLE: {a.title}\nCOMPANY: {a.company}\nLOCATION: {a.location}\nPOSTED: {a.posted}\n"
           f"URL: {a.link}\nSOURCE: {a.source}\nAPPLICANTS: \n---\n")
    open(os.path.join(out, "jd", f"{jid}.txt"), "w", encoding="utf-8").write(hdr + desc)
print(jid)
