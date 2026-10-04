"""Open CVs (and cover letters) in the computer's PDF viewer, so the user sees them before saying yes.

  python3 kit/preview.py 3 7        # jobs 3 and 7
  python3 kit/preview.py master     # the general CV

Prints the paths too, for when nothing can be opened (a remote machine).
"""
import argparse, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_profile, job_dirs, cv_pdfs, letter_path

ap = argparse.ArgumentParser()
ap.add_argument("which", nargs="+", help="job numbers and/or 'master'")
ap.add_argument("--workspace")
a = ap.parse_args()
ws = workspace(a.workspace)
name = load_profile(ws)["name"]
dirs = job_dirs(ws)
files = []
for w in a.which:
    d = os.path.join(ws, "master") if w == "master" else dirs.get(int(w)) if w.isdigit() else None
    if not d:
        print(f"{w}: no such job folder")
        continue
    letter = letter_path(d, name)
    found = cv_pdfs(d, name) + ([letter] if os.path.exists(letter) else [])
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
