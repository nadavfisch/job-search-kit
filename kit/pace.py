"""LinkedIn pace check: run right before every LinkedIn submission (Easy Apply).

  python3 kit/pace.py [--per-day 15] [--per-hour 5] [--gap 3]

Counts today's "submitted" events in my-search/log.md whose details mention LinkedIn or Easy Apply.
Exit 0 = OK to submit now; exit 1 = wait (the gap or the hourly cap) or stop for today (the daily cap).
LinkedIn restricts accounts mostly on behavior: dozens of applications in a row at machine speed is what it
looks for. A human pace keeps the account safe. The user can change the limits (preferences.md).
"""
import argparse, datetime, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace

ap = argparse.ArgumentParser()
ap.add_argument("--per-day", type=int, default=15); ap.add_argument("--per-hour", type=int, default=5)
ap.add_argument("--gap", type=int, default=3, help="minutes between submissions")
ap.add_argument("--workspace")
a = ap.parse_args()
path = os.path.join(workspace(a.workspace), "log.md")
now = datetime.datetime.now()
times = []
for l in open(path, encoding="utf-8") if os.path.exists(path) else []:
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    m = re.match(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?", c[0]) if l.startswith("|") and len(c) >= 5 else None
    if m and c[3] == "submitted" and re.search(r"linkedin|easy apply", c[4], re.I):
        times.append(datetime.datetime.fromisoformat(f"{m.group(1)} {m.group(2) or '00:00'}"))
today = [t for t in times if t.date() == now.date()]
hour = [t for t in today if now - t < datetime.timedelta(hours=1)]
last = max(today, default=None)
mins = int((now - last).total_seconds() // 60) if last else None
status = f"{len(today)}/{a.per_day} today, {len(hour)}/{a.per_hour} this hour" + (f", last {mins} min ago" if last else "")
if len(today) >= a.per_day:
    sys.exit(f"STOP for today: {status}. Continue tomorrow, or with company-site applications.")
if len(hour) >= a.per_hour:
    sys.exit(f"WAIT: {status}. Work on something else and check again later.")
if last and mins < a.gap:
    sys.exit(f"WAIT {a.gap - mins} min: {status}.")
print(f"OK: {status}")
