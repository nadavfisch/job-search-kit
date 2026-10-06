"""Where the search stands: the pipeline, what's waiting on you, and what's working.

  python3 kit/stats.py

Reads tracker.md and log.md. "Responded" = a Response is filled in, the status is interview / rejected / offer,
or log.md has a reply / interview / assessment / rejected / offer event for the job.
"""

import argparse
import collections
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, read_tracker, read_text, cells


def day(s):
    m = re.search(r"\d{4}-\d{2}-\d{2}", s or "")
    return datetime.date.fromisoformat(m.group()) if m else None


def status(r):
    return (r.get("Status", "").split() or [""])[0].lower()


def pct(x, y):
    return f"{100 * x // y}%" if y else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    today = datetime.date.today()
    rows = [r for r in read_tracker(ws) if r.get("#", "").isdigit()]
    log = []
    log_path = os.path.join(ws, "log.md")
    for line in read_text(log_path).split("\n") if os.path.exists(log_path) else []:
        c = cells(line)
        if line.startswith("|") and len(c) >= 4 and day(c[0]):
            log.append(dict(date=day(c[0]), job=c[1], company=c[2], event=c[3], details=c[4] if len(c) > 4 else ""))
    interviewed = {e["job"] for e in log if e["event"] in ("interview", "offer")}
    answered = {e["job"] for e in log if e["event"] in ("reply", "interview", "assessment", "rejected", "offer")}

    sent = [r for r in rows if day(r.get("Submitted"))]
    responded = [
        r for r in sent if r.get("Response") or status(r) in ("interview", "rejected", "offer") or r["#"] in answered
    ]
    interviews = [r for r in sent if status(r) in ("interview", "offer") or r["#"] in interviewed]

    print(f"# Job search, {today}\n")
    print(
        "Pipeline: "
        + ("(no jobs yet)" if not rows else "")
        + ", ".join(f"{k or '(none)'} {v}" for k, v in collections.Counter(map(status, rows)).most_common())
    )
    print(
        f"Submitted {len(sent)} · responded {len(responded)} ({pct(len(responded), len(sent))}) · "
        f"interviews {len(interviews)} ({pct(len(interviews), len(sent))}) · offers {sum(status(r) == 'offer' for r in sent)}"
    )

    src = collections.defaultdict(lambda: [0, 0, 0])
    for r in sent:
        s = src[r.get("Source") or "?"]
        s[0] += 1
        s[1] += r in responded
        s[2] += r in interviews
    if src:
        print("\n| Source | Submitted | Responded | Interviews |\n|---|---|---|---|")
        for k, (n, rs, iv) in sorted(src.items(), key=lambda x: -x[1][0]):
            print(f"| {k} | {n} | {rs} ({pct(rs, n)}) | {iv} ({pct(iv, n)}) |")

    waiting = [r for r in rows if not r.get("Submitted") and re.match(r"(apply|stretch)\b", r.get("Status", ""), re.I)]
    due = [
        r
        for r in sent
        if r not in responded and status(r) == "submitted" and day(r.get("Follow-up")) and day(r["Follow-up"]) <= today
    ]
    stale = [
        r for r in sent if r not in responded and status(r) == "submitted" and (today - day(r["Submitted"])).days >= 21
    ]
    for title, group in (("Waiting to submit", waiting), ("Follow-ups due", due), ("No answer for 3+ weeks", stale)):
        if group:
            print(f"\n## {title} ({len(group)})")
            for r in group:
                print(
                    f"- #{r['#']} {r.get('Company', '')}, {r.get('Role', '')}"
                    + (f" (submitted {r['Submitted']})" if r.get("Submitted") else "")
                )
    week = [e for e in log if (today - e["date"]).days < 7]
    if week:
        print(
            "\nLast 7 days: "
            + ", ".join(f"{k} {v}" for k, v in collections.Counter(e["event"] for e in week).most_common())
        )


if __name__ == "__main__":
    main()
