"""Record an event in my-search/log.md (the dated history of the whole search).

  python3 kit/log.py <event> [--job N] [--company X] [--details "..."] [--date YYYY-MM-DD]

Events: added, submitted, message-sent, follow-up-sent, reply, interview, assessment, rejected, offer,
withdrawn, closed, note. --job fills the company from the tracker.
"""
import argparse, datetime, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, read_tracker, append_row

EVENTS = {"added", "submitted", "message-sent", "follow-up-sent", "reply", "interview", "assessment",
          "rejected", "offer", "withdrawn", "closed", "note"}
ap = argparse.ArgumentParser()
ap.add_argument("event"); ap.add_argument("--job", type=int); ap.add_argument("--company", default="")
ap.add_argument("--details", default=""); ap.add_argument("--date", default=datetime.date.today().isoformat())
ap.add_argument("--workspace")
a = ap.parse_args()
if a.event not in EVENTS:
    sys.exit(f"Unknown event '{a.event}'. One of: {', '.join(sorted(EVENTS))}")
ws = workspace(a.workspace)
path = os.path.join(ws, "log.md")
if not os.path.exists(path):
    sys.exit("No log.md: copy templates/log.md into the workspace.")
company = a.company or next((r.get("Company", "") for r in read_tracker(ws) if a.job and r.get("#") == str(a.job)), "")
append_row(path, [a.date, a.job or "", company, a.event, a.details])
print(f"logged: {a.date} {a.event} {company}")
