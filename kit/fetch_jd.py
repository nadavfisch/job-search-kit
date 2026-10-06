"""Fetch LinkedIn job descriptions (other sources save theirs during kit/search.py) into my-search/batches/<batch>/jd/<id>.txt.

  python3 kit/fetch_jd.py <batch> <new|all|id1,id2,...>

Each file starts with a header (title, company, posted, applicants, URL), then the description.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_json, write_text
import sources


def main():
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
    li = [i for i in jobs if i.isdigit()]  # other sources save their descriptions during the search
    if a.which == "all":
        ids = li
    elif a.which == "new":
        ids = [i for i in li if jobs[i].get("new", True)]
    else:
        ids = a.which.split(",")
    fetched = empty = 0
    for jid in ids:
        out = os.path.join(jd_dir, f"{jid}.txt")
        if os.path.exists(out) and os.path.getsize(out) > 300:  # already fetched (more than the header)
            continue
        try:
            post = sources.linkedin_posting(sources.get(sources.linkedin_posting_url(jid)))
        except Exception as e:
            print(jid, "ERR", e)
            time.sleep(3)
            continue
        j = jobs.get(jid, {})
        hdr = (
            f"ID: {jid}\nTITLE: {j.get('title', '')}\nCOMPANY: {j.get('company', '')}\nLOCATION: {j.get('location', '')}\n"
            f"POSTED: {j.get('date', '')}\nURL: https://www.linkedin.com/jobs/view/{jid}\nSOURCE: linkedin\n"
            f"APPLICANTS: {post['applicants']}\nCRITERIA: {post['criteria']}\n---\n"
        )
        write_text(out, hdr + post["description"])
        fetched += 1
        empty += not post["description"]
        print(jid, len(post["description"]) or "EMPTY (closed, or blocked: don't triage an empty description)")
        time.sleep(1.5)
    if fetched > 1 and empty == fetched:
        print(
            f"None of the {fetched} descriptions came through. LinkedIn may be blocking for now (wait, then retry). "
            f"If it keeps happening: {sources.LINKEDIN_CHANGED}."
        )


if __name__ == "__main__":
    main()
