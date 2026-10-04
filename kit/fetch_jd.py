"""Fetch LinkedIn job descriptions (other sources save theirs during kit/search.py) into my-search/batches/<batch>/jd/<id>.txt.

  python3 kit/fetch_jd.py <batch> <new|all|id1,id2,...>

Each file starts with a header (title, company, posted, applicants, URL), then the description.
"""
import argparse, html, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_json, write_text
import sources

ap = argparse.ArgumentParser()
ap.add_argument("batch")
ap.add_argument("which", help="new, all, or job ids separated by commas")
ap.add_argument("--workspace")
a = ap.parse_args()
data = os.path.join(workspace(a.workspace), "batches", a.batch)
if not os.path.exists(os.path.join(data, "jobs_all.json")):
    sys.exit(f"No batch at {data}. Run kit/search.py first.")
jd_dir = os.path.join(data, "jd")
os.makedirs(jd_dir, exist_ok=True)
jobs = load_json(os.path.join(data, "jobs_all.json"))
li = [i for i in jobs if i.isdigit()]   # other sources save their descriptions during the search
if a.which == "all":
    ids = li
elif a.which == "new":
    ids = [i for i in li if jobs[i].get("new", True)]
else:
    ids = a.which.split(",")
for jid in ids:
    out = os.path.join(jd_dir, f"{jid}.txt")
    if os.path.exists(out) and os.path.getsize(out) > 300:   # already fetched (more than the header)
        continue
    try:
        t = sources.get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}")
    except Exception as e:
        print(jid, "ERR", e)
        time.sleep(3)
        continue
    m = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", t, re.S)
    d = sources.text(m.group(1)) if m else ""
    crit = re.findall(r'description__job-criteria-subheader">\s*(.*?)\s*</h3>\s*<span[^>]*>\s*(.*?)\s*</span>', t, re.S)
    applicants = re.search(r"num-applicants__caption[^>]*>\s*(.*?)\s*<", t, re.S)
    j = jobs.get(jid, {})
    hdr = (f"ID: {jid}\nTITLE: {j.get('title', '')}\nCOMPANY: {j.get('company', '')}\nLOCATION: {j.get('location', '')}\n"
           f"POSTED: {j.get('date', '')}\nURL: https://www.linkedin.com/jobs/view/{jid}\nSOURCE: linkedin\n"
           f"APPLICANTS: {applicants.group(1).strip() if applicants else ''}\n"
           f"CRITERIA: {'; '.join(k + ': ' + html.unescape(v) for k, v in crit)}\n---\n")
    write_text(out, hdr + d)
    print(jid, len(d) if d else "EMPTY (closed, or blocked: don't triage an empty description)")
    time.sleep(1.5)
