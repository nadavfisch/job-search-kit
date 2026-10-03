"""Fetch LinkedIn job descriptions (other sources save theirs during kit/search.py) into my-search/batches/<batch>/jd/<id>.txt.

  python3 kit/fetch_jd.py <batch> <new|all|id1,id2,...>

Each file starts with a header (title, company, posted, applicants, URL), then the description.
"""
import html, json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
if len(sys.argv) < 3:
    sys.exit(__doc__)
data = os.path.join(workspace(), "batches", sys.argv[1])
jd_dir = os.path.join(data, "jd")
os.makedirs(jd_dir, exist_ok=True)
jobs = json.load(open(os.path.join(data, "jobs_all.json"), encoding="utf-8"))
which = sys.argv[2]
li = [i for i in jobs if i.isdigit()]   # other sources save their descriptions during the search
ids = li if which == "all" else [i for i in li if jobs[i].get("new", True)] if which == "new" else which.split(",")
for jid in ids:
    out = os.path.join(jd_dir, f"{jid}.txt")
    if os.path.exists(out) and os.path.getsize(out) > 300:
        continue
    try:
        req = urllib.request.Request(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}", headers={"User-Agent": UA})
        t = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    except Exception as e:
        print(jid, "ERR", e); time.sleep(3); continue
    m = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", t, re.S)
    d = m.group(1) if m else ""
    d = re.sub(r"<br\s*/?>|</p>|</li>|<li>", "\n", d)
    d = html.unescape(re.sub(r"<[^>]+>", "", d))
    d = re.sub(r"\n\s*\n+", "\n", d).strip()
    crit = re.findall(r'description__job-criteria-subheader">\s*(.*?)\s*</h3>\s*<span[^>]*>\s*(.*?)\s*</span>', t, re.S)
    applicants = re.search(r"num-applicants__caption[^>]*>\s*(.*?)\s*<", t, re.S)
    j = jobs.get(jid, {})
    hdr = (f"ID: {jid}\nTITLE: {j.get('title', '')}\nCOMPANY: {j.get('company', '')}\nLOCATION: {j.get('location', '')}\n"
           f"POSTED: {j.get('date', '')}\nURL: https://www.linkedin.com/jobs/view/{jid}\nSOURCE: linkedin\n"
           f"APPLICANTS: {applicants.group(1).strip() if applicants else ''}\n"
           f"CRITERIA: {'; '.join(a + ': ' + html.unescape(b) for a, b in crit)}\n---\n")
    open(out, "w", encoding="utf-8").write(hdr + d)
    print(jid, len(d) if d else "EMPTY (closed, or blocked: don't triage an empty description)")
    time.sleep(1.5)
