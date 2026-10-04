"""Add a job lead from anywhere (an email alert, a friend, a job site) to a search batch, so it gets triaged
with the rest.

  python3 kit/add_lead.py --batch 2026-10-03 --source alljobs --company "Acme" --title "Ops Lead" \
      --link https://... [--location "Tel Aviv"] [--posted 2026-10-01] [--jd -]      # --jd - reads the description from stdin

Prints the lead's id (for new_job.py --batch <date> --id <id>). Without --jd, open the link and add the
description before triage: a lead is never triaged on its title alone.
"""
import argparse, hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_json, save_json, read_text, write_text

ap = argparse.ArgumentParser()
ap.add_argument("--batch", required=True); ap.add_argument("--source", required=True)
ap.add_argument("--company", required=True); ap.add_argument("--title", required=True); ap.add_argument("--link", required=True)
ap.add_argument("--location", default=""); ap.add_argument("--posted", default=""); ap.add_argument("--jd")
ap.add_argument("--workspace")
a = ap.parse_args()
ws = workspace(a.workspace)
if a.jd and a.jd != "-" and not os.path.exists(a.jd):
    sys.exit(f"No description file at {a.jd}")
out = os.path.join(ws, "batches", a.batch)
os.makedirs(os.path.join(out, "jd"), exist_ok=True)
jobs_file = os.path.join(out, "jobs_all.json")
jobs = load_json(jobs_file)
jid = "lead-" + hashlib.sha1(a.link.encode(), usedforsecurity=False).hexdigest()[:10]   # a stable id, not security
if jid in jobs:
    sys.exit(f"{jid}: already in batch {a.batch}")
desc = (sys.stdin.read() if a.jd == "-" else read_text(a.jd)) if a.jd else None
jobs[jid] = dict(id=jid, title=a.title, company=a.company, location=a.location, date=a.posted, url=a.link, source=a.source, new=True, q=[])
save_json(jobs_file, jobs)
if desc is not None:
    hdr = (f"ID: {jid}\nTITLE: {a.title}\nCOMPANY: {a.company}\nLOCATION: {a.location}\nPOSTED: {a.posted}\n"
           f"URL: {a.link}\nSOURCE: {a.source}\nAPPLICANTS: \n---\n")
    write_text(os.path.join(out, "jd", f"{jid}.txt"), hdr + desc)
print(jid)
