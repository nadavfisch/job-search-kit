"""Open CVs (and cover letters) in the computer's PDF viewer, so the user sees them before saying yes.

  python3 kit/preview.py 3 7        # jobs 3 and 7
  python3 kit/preview.py master     # the general CV

Prints the paths too, for when nothing can be opened (a remote machine).
"""
import argparse, glob, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_profile, job_dirs, safe

ap = argparse.ArgumentParser()
ap.add_argument("which", nargs="+", help="job numbers and/or 'master'")
ap.add_argument("--workspace")
a = ap.parse_args()
ws = workspace(a.workspace)
name = safe(load_profile(ws)["name"])
dirs = job_dirs(ws)
files = []
for w in a.which:
    d = os.path.join(ws, "master") if w == "master" else dirs.get(int(w)) if w.isdigit() else None
    found = sorted(glob.glob(os.path.join(glob.escape(d), f"{glob.escape(name)} - *.pdf"))) if d else []
    if not found:
        print(f"{w}: no PDF yet (run kit/build.py {w})")
    files += found
for f in files:
    print(f)
if files:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", *files], check=False)
        elif sys.platform.startswith("win"):
            for f in files:
                os.startfile(f)
        else:
            for f in files:
                subprocess.run(["xdg-open", f], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"couldn't open a viewer ({e}): open the paths above")
