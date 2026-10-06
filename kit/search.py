"""Find jobs from every source in my-search/search.yaml into my-search/batches/<date>/.

  python3 kit/search.py [batch] [--only linkedin,companies,remote]     # batch = a date tag, default today

Sources:
  linkedin   LinkedIn's public (logged-out) job search. Descriptions: kit/fetch_jd.py <batch> new
  companies  target companies' own job boards (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Comeet),
             filtered by title_keywords / title_exclude / locations. Descriptions are saved right away.
  remote     remote job boards (Remotive), one search per remote.queries entry.
Results merge into batches/<batch>/jobs_all.json. Jobs seen in an earlier batch are marked "new": false.

LinkedIn's User Agreement forbids automated access: keep the volume low and use it at your own risk.
"""

import argparse
import datetime
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_yaml, load_json, save_json, write_text
import sources

SOURCES = ("linkedin", "companies", "remote")


def wanted(j, keywords, exclude, locations, cutoff):
    """Does a job pass search.yaml's filters? cutoff = the oldest posting date wanted (YYYY-MM-DD)."""
    t, loc = (j["title"] or "").lower(), (j["location"] or "").lower()

    def word(k):  # a whole word: "AI" matches "AI Lead", not "Retail"
        return re.search(rf"(?<![a-z0-9]){re.escape(k.lower())}(?![a-z0-9])", t)

    if keywords and not any(word(k) for k in keywords):
        return False
    if any(word(x) for x in exclude):
        return False
    if locations and not any(place.lower() in loc for place in locations):
        return False
    return not (j["date"] and j["date"][:10] < cutoff)


def search_linkedin(li, days, add):
    results = unread = untitled = 0
    for q in li["queries"]:
        start = size = 0
        got = set()
        while start < sources.LINKEDIN_PER_QUERY:
            url = sources.linkedin_search_url(q, li.get("location", ""), li.get("geo_id"), days, start)
            try:
                t = sources.get(url)
            except Exception:
                t = ""
            cards = sources.linkedin_cards(t)
            unread += not cards and not sources.linkedin_empty(t)
            fresh = [j for j in cards if j["id"] not in got]
            got.update(j["id"] for j in fresh)
            for j in fresh:
                add(j, q)
                untitled += not (j["title"] and j["company"])
            results += len(fresh)
            time.sleep(1.2)
            size = size or len(cards)  # the page size is whatever the first page had
            if not fresh or len(cards) < size:  # the last page, or LinkedIn repeating a page
                break
            start += len(cards)
    if not results and unread:
        print(f"LinkedIn sent pages the kit couldn't read. If it's the same after a pause: {sources.LINKEDIN_CHANGED}.")
    elif not results:
        print("LinkedIn: nothing came back (maybe rate-limited). Wait and retry, or search by hand.")
    elif untitled:
        print(f"LinkedIn: {untitled} jobs came back without a title or company. {sources.LINKEDIN_CHANGED}.")


def search_companies(cfg, cutoff, add):
    kw, ex, locs = cfg.get("title_keywords") or [], cfg.get("title_exclude") or [], cfg.get("locations") or []
    for c in cfg.get("companies") or []:
        fetch = sources.ATS.get(c.get("ats", ""))
        if not fetch:
            print(f"{c.get('name')}: unknown ats '{c.get('ats')}' (one of {', '.join(sources.ATS)})")
            continue
        try:
            hits = [j for j in fetch(c) if wanted(j, kw, ex, locs, cutoff)]
        except Exception as e:
            print(
                f"{c.get('name')}: failed ({e}). Check the slug / url with: python3 kit/sources.py detect <careers url>"
            )
            continue
        for j in hits:
            add(j)
        print(f"{c.get('name')}: {len(hits)} matching")


def search_remote(cfg, cutoff, add):
    rem = cfg.get("remote") or {}
    allowed = [x.lower() for x in rem.get("allowed_locations") or []]
    for q in rem.get("queries") or []:
        try:
            for j in sources.remotive(q):
                if (not allowed or any(x in j["location"].lower() for x in allowed)) and wanted(
                    j, [], cfg.get("title_exclude") or [], [], cutoff
                ):
                    add(j, q)
        except Exception as e:
            print(f"Remotive '{q}': failed ({e})")
        time.sleep(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", nargs="?", default=datetime.date.today().isoformat())
    ap.add_argument("--only", default=",".join(SOURCES))
    ap.add_argument("--workspace")
    a = ap.parse_args()
    only = set(a.only.split(","))
    if only - set(SOURCES):
        ap.error(f"--only takes {', '.join(SOURCES)} (got: {', '.join(sorted(only - set(SOURCES)))})")
    ws = workspace(a.workspace)
    cfg = load_yaml(os.path.join(ws, "search.yaml"))
    out_dir = os.path.join(ws, "batches", a.batch)
    jd_dir = os.path.join(out_dir, "jd")
    os.makedirs(jd_dir, exist_ok=True)
    jobs_file = os.path.join(out_dir, "jobs_all.json")
    jobs = load_json(jobs_file)
    seen = set()  # job ids from every earlier batch
    for b in os.listdir(os.path.join(ws, "batches")):
        if os.path.join(ws, "batches", b) != out_dir:
            seen |= set(load_json(os.path.join(ws, "batches", b, "jobs_all.json")))
    days = int(cfg.get("days", 14))
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).date().isoformat()
    counts = {}

    def add(j, query=None):
        if j["id"] in jobs:
            if query and query not in jobs[j["id"]].setdefault("q", []):
                jobs[j["id"]]["q"].append(query)
            return
        desc = j.pop("description", "")
        jobs[j["id"]] = dict(j, new=j["id"] not in seen, q=[query] if query else [])
        counts[j["source"]] = counts.get(j["source"], 0) + 1
        if desc is not None and not j["id"].isdigit():
            if callable(desc):
                try:
                    desc = desc()
                except Exception as e:
                    desc = ""
                    print(f"  {j['id']}: description failed ({e})")
            hdr = (
                f"ID: {j['id']}\nTITLE: {j['title']}\nCOMPANY: {j['company']}\nLOCATION: {j['location']}\n"
                f"POSTED: {j['date']}\nURL: {j['url']}\nSOURCE: {j['source']}\nAPPLICANTS: \n---\n"
            )
            write_text(os.path.join(jd_dir, f"{j['id']}.txt"), hdr + (desc or ""))

    li = cfg.get("linkedin") or {k: cfg[k] for k in ("queries", "location", "geo_id") if k in cfg}
    if "linkedin" in only and li.get("queries"):
        search_linkedin(li, days, add)
    if "companies" in only:
        search_companies(cfg, cutoff, add)
    if "remote" in only:
        search_remote(cfg, cutoff, add)

    save_json(jobs_file, jobs)
    new = sum(1 for j in jobs.values() if j.get("new"))
    print(
        f"{len(jobs)} jobs in batch {a.batch} ({new} new). Added now: "
        + (", ".join(f"{k} {v}" for k, v in counts.items()) or "none")
        + f"\n-> {jobs_file}"
    )
    if counts.get("linkedin"):
        print(f"Next: python3 kit/fetch_jd.py {a.batch} new")


if __name__ == "__main__":
    main()
