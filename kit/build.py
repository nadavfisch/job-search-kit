"""Check and render tailored CVs.

  python3 kit/build.py              # every job in my-search/jobs/ that has a filled spec.yaml
  python3 kit/build.py 3 7          # jobs 3 and 7
  python3 kit/build.py master       # the general CV straight from profile.yaml -> my-search/master/
  --check       run the checks only, render nothing
  --force       also re-render jobs the tracker marks as submitted (overwrites the PDF the company already has)
  --workspace   data folder (default: my-search/)

Nothing renders if any spec fails a check. The checks:
  - every bullet is a key from profile.yaml, or {from: key, text: ...} (a rewording of that key, same facts)
  - a bullet sits under the role it belongs to; no role or bullet twice; no two bullets from one overlap group
  - every number in the CV appears in profile.yaml; a reworded bullet adds no number its source doesn't have
  - none of the user's banned patterns (profile.yaml rules) appear
Experience always renders in profile.yaml order (reverse-chronological). Tailor through the title,
summary, and bullet choice, never through order.
"""
import argparse, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_profile, load_yaml, roles, bullets, read_tracker, job_dirs, safe
from render import render


def nums(t):
    """Standalone numbers: '80%' -> 80, '10M+' -> 10M. Skips 'B2B', 'Web3', '0-to-1'."""
    t = re.sub(r"\b0-to-1\b", "", str(t))
    return {n.replace(",", "") + s.upper() for n, s in re.findall(r"(?<![A-Za-z0-9])(\d[\d,]*(?:\.\d+)?)([KkMm]?)(?![A-Za-z0-9])", t)}


def source_numbers(p):
    texts = [p.get("headline", ""), p.get("summary", ""), p.get("languages", ""), *(p.get("education") or [])]
    for r in p["experience"]:
        texts += [r.get("header", ""), *(r.get("bullets") or {}).values()]
    texts += [s.get("text", "") for s in (p.get("skills") or {}).values()]
    return nums(" ".join(map(str, texts)))


def master_spec(p):
    return {"title": p.get("headline", ""), "summary": p.get("summary", ""),
            "experience": [{"role": r["key"], "bullets": r.get("default") or list((r.get("bullets") or {}).keys())}
                           for r in p["experience"]],
            "skills": list((p.get("skills") or {}).keys())}


def problems(p, raw):
    """Return (errors, normalized spec)."""
    R, B, S = roles(p), bullets(p), p.get("skills") or {}
    rules = p.get("rules") or {}
    src_nums = source_numbers(p)
    err, used, texts = [], [], []
    if not raw.get("title"):
        err.append("no title")
    texts.append(("title", raw.get("title", "")))
    texts.append(("summary", raw.get("summary", "")))
    exp, seen_roles = [], []
    for e in raw.get("experience") or []:
        rk = e.get("role")
        if rk not in R:
            err.append(f"unknown role '{rk}' (keys: {', '.join(R)})"); continue
        if rk in seen_roles:
            err.append(f"role '{rk}' listed twice")
        seen_roles.append(rk)
        out = []
        for b in e.get("bullets") or []:
            if isinstance(b, str):
                if b not in B:
                    err.append(f"'{b[:50]}' is not a bullet key. Free text must be {{from: <key>, text: ...}}"); continue
                key, text = b, B[b][1]
            elif isinstance(b, dict) and b.get("from") and b.get("text"):
                key, text = b["from"], str(b["text"])
                if key not in B:
                    err.append(f"reworded bullet: unknown source key '{key}'"); continue
                extra = nums(text) - nums(B[key][1])
                if extra:
                    err.append(f"reworded '{key}' adds numbers its source doesn't have: {', '.join(sorted(extra))}")
            else:
                err.append(f"bad bullet entry under '{rk}': {b!r}"); continue
            if B[key][0] != rk:
                err.append(f"bullet '{key}' belongs to role '{B[key][0]}', not '{rk}'")
            used.append(key)
            out.append(text)
            texts.append((f"bullet '{key}'", text))
        exp.append((rk, out))
    order = list(R)
    exp.sort(key=lambda x: order.index(x[0]))
    err += [f"bullet '{k}' used twice" for k in sorted({k for k in used if used.count(k) > 1})]
    for group in rules.get("overlaps") or []:
        hit = [k for k in group if k in used]
        if len(hit) > 1:
            err.append(f"overlapping bullets (same content): {', '.join(hit)}")
    skills = []
    for s in raw.get("skills") or []:
        if isinstance(s, str):
            if s not in S:
                err.append(f"unknown skills line '{s}' (keys: {', '.join(S)})"); continue
            skills.append((S[s]["label"], S[s]["text"]))
        elif isinstance(s, dict) and s.get("label") and s.get("text"):
            skills.append((s["label"], s["text"]))
        else:
            err.append(f"bad skills entry: {s!r}"); continue
        texts.append((f"skills '{skills[-1][0]}'", skills[-1][1]))
    for where, t in texts:
        extra = nums(t) - src_nums
        if extra:
            err.append(f"{where}: numbers not in profile.yaml: {', '.join(sorted(extra))}")
        for rule in rules.get("banned") or []:
            if re.search(rule["pattern"], str(t), re.I):
                err.append(f"{where}: {rule.get('why', 'banned pattern ' + rule['pattern'])}")
    if rules.get("title_banned") and re.search(rules["title_banned"], raw.get("title", ""), re.I):
        err.append(f"title inflates level: {raw.get('title')}")
    spec = {"title": raw.get("title", ""), "summary": raw.get("summary", ""), "experience": exp,
            "skills": skills, "education": raw.get("education", True)}
    return err, spec


def frozen(ws):
    """{job number: reason} for jobs whose PDF the company already has (tracker 'Submitted' filled)."""
    return {int(r["#"]): f"submitted {r['Submitted']}" for r in read_tracker(ws)
            if r.get("#", "").isdigit() and r.get("Submitted")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", help="job numbers and/or 'master'; empty = every job")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    p = load_profile(ws)
    dirs = job_dirs(ws)
    want = [int(x) for x in a.only if x.isdigit()]
    todo, errors = [], []
    if "master" in a.only:
        e, spec = problems(p, master_spec(p))
        errors += [f"master: {x}" for x in e]
        todo.append(("master", spec, os.path.join(ws, "master")))
    for n in (want or ([] if "master" in a.only else sorted(dirs))):
        d = dirs.get(n)
        path = os.path.join(d, "spec.yaml") if d else None
        if not path or not os.path.exists(path):
            errors.append(f"#{n}: no job folder with a spec.yaml"); continue
        raw = load_yaml(path)
        if not raw.get("title") and not want:
            print(f"#{n}: spec.yaml not filled yet, skipped"); continue
        e, spec = problems(p, raw)
        errors += [f"#{n} {raw.get('company', '')}: {x}" for x in e]
        todo.append((n, spec, d))
    if errors:
        sys.exit("Spec errors, nothing rendered:\n  " + "\n  ".join(errors))
    if a.check:
        sys.exit(print(f"OK: {len(todo)} spec(s) pass, nothing rendered (--check)"))
    done = {} if a.force else frozen(ws)
    name = safe(p["name"])
    for n, spec, d in todo:
        if n in done:
            print(f"#{n}: skipped, {done[n]} (--force overwrites the PDF the company has)"); continue
        out = os.path.join(d, f"{name} - {safe(spec['title'])}.pdf")
        for old in glob.glob(os.path.join(d, f"{glob.escape(name)} - *.pdf")):
            if old != out:
                os.remove(old)   # an earlier render under a different title
        step = render(p, spec, out)
        print(f"#{n}: " + ("DOESN'T FIT: cut or shorten bullets" if step == "OVERFLOW" else out))


if __name__ == "__main__":
    main()
