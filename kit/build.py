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

import argparse
import decimal
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import workspace, load_profile, load_yaml, roles, bullets, read_tracker, job_dirs, cv_path, cv_pdfs
from render import render

# A number as written in a CV: "45%", "2,000", "99.9", "10x", "$1.5M", "$2B", "10 million", "200ms".
NUMBER = re.compile(
    r"(?<![A-Za-z0-9.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?"
    r"(?:\s?(thousand|million|billion|mm|mn|bn|k|m|b)(?![A-Za-z0-9]))?",
    re.I,
)
SCALE = {"k": 3, "thousand": 3, "m": 6, "mm": 6, "mn": 6, "million": 6, "b": 9, "bn": 9, "billion": 9}


def nums(t):
    """{value: as written} for every number in t, so '2,000', '2K' and '2 thousand' are the same number.
    A unit stuck to a number doesn't hide it ('10x', '200ms' -> 10, 200). Skips names like 'B2B', 'Web3',
    'v2.0' and '0-to-1'."""
    found = {}
    for m in NUMBER.finditer(re.sub(r"\b0-to-1\b", "", str(t))):
        whole, frac, scale = m.groups()
        value = decimal.Decimal(whole.replace(",", "") + (frac or "")).scaleb(SCALE.get((scale or "").lower(), 0))
        found.setdefault(format(value.normalize(), "f"), m.group().strip())
    return found


def new_numbers(t, known):
    """The numbers in t that aren't in `known` (a set of values from nums), as written."""
    found = nums(t)
    return sorted(found[v] for v in found.keys() - known)


def source_numbers(p):
    texts = [p.get("headline", ""), p.get("summary", ""), p.get("languages", ""), *(p.get("education") or [])]
    for r in p["experience"]:
        texts += [r.get("header", ""), *(r.get("bullets") or {}).values()]
    texts += [s.get("text", "") for s in (p.get("skills") or {}).values()]
    return set().union(*map(nums, texts))


def master_spec(p):
    return {
        "title": p.get("headline", ""),
        "summary": p.get("summary", ""),
        "experience": [
            {"role": r["key"], "bullets": r.get("default") or list((r.get("bullets") or {}).keys())}
            for r in p["experience"]
        ],
        "skills": list((p.get("skills") or {}).keys()),
    }


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
        if not isinstance(e, dict):
            err.append(f"bad experience entry {e!r}: each one is {{role: <role key>, bullets: [...]}}")
            continue
        rk = e.get("role")
        if rk not in R:
            err.append(f"unknown role '{rk}' (keys: {', '.join(R)})")
            continue
        if rk in seen_roles:
            err.append(f"role '{rk}' listed twice")
        seen_roles.append(rk)
        out = []
        for b in e.get("bullets") or []:
            if isinstance(b, str):
                if b not in B:
                    err.append(f"'{b[:50]}' is not a bullet key. Free text must be {{from: <key>, text: ...}}")
                    continue
                key, text = b, B[b][1]
            elif isinstance(b, dict) and b.get("from") and b.get("text"):
                key, text = b["from"], str(b["text"])
                if key not in B:
                    err.append(f"reworded bullet: unknown source key '{key}'")
                    continue
                extra = new_numbers(text, set(nums(B[key][1])))
                if extra:
                    err.append(f"reworded '{key}' adds numbers its source doesn't have: {', '.join(extra)}")
            else:
                err.append(f"bad bullet entry under '{rk}': {b!r}")
                continue
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
                err.append(f"unknown skills line '{s}' (keys: {', '.join(S)})")
                continue
            skills.append((S[s]["label"], S[s]["text"]))
        elif isinstance(s, dict) and s.get("label") and s.get("text"):
            skills.append((s["label"], s["text"]))
        else:
            err.append(f"bad skills entry: {s!r}")
            continue
        texts.append((f"skills '{skills[-1][0]}'", skills[-1][1]))
    for where, t in texts:
        extra = new_numbers(t, src_nums)
        if extra:
            err.append(f"{where}: numbers not in profile.yaml: {', '.join(extra)}")
        for rule in rules.get("banned") or []:
            if re.search(rule["pattern"], str(t), re.I):
                err.append(f"{where}: {rule.get('why', 'banned pattern ' + rule['pattern'])}")
    if rules.get("title_banned") and re.search(rules["title_banned"], raw.get("title", ""), re.I):
        err.append(f"title inflates level: {raw.get('title')}")
    spec = {
        "title": raw.get("title", ""),
        "summary": raw.get("summary", ""),
        "experience": exp,
        "skills": skills,
        "education": raw.get("education", True),
    }
    return err, spec


def frozen(ws):
    """{job number: reason} for jobs whose PDF the company already has (tracker 'Submitted' filled)."""
    return {
        int(r["#"]): f"submitted {r['Submitted']}"
        for r in read_tracker(ws)
        if r.get("#", "").isdigit() and r.get("Submitted")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", help="job numbers and/or 'master'; empty = every job")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    unknown = [x for x in a.only if not x.isdigit() and x != "master"]
    if unknown:
        ap.error(f"not a job number or 'master': {', '.join(unknown)}")
    ws = workspace(a.workspace)
    p = load_profile(ws)
    dirs = job_dirs(ws)
    want = [int(x) for x in a.only if x.isdigit()]
    todo, errors = [], []
    if "master" in a.only:
        e, spec = problems(p, master_spec(p))
        errors += [f"master: {x}" for x in e]
        todo.append(("master", spec, os.path.join(ws, "master")))
    for n in want or ([] if "master" in a.only else sorted(dirs)):
        d = dirs.get(n)
        path = os.path.join(d, "spec.yaml") if d else None
        if not path or not os.path.exists(path):
            errors.append(f"#{n}: no job folder with a spec.yaml")
            continue
        raw = load_yaml(path)
        if not raw.get("title") and not want:
            print(f"#{n}: spec.yaml not filled yet, skipped")
            continue
        e, spec = problems(p, raw)
        errors += [f"#{n} {raw.get('company', '')}: {x}" for x in e]
        todo.append((n, spec, d))
    if errors:
        sys.exit("Spec errors, nothing rendered:\n  " + "\n  ".join(errors))
    if not todo:
        print("No filled spec.yaml to build yet.")
        return
    if a.check:
        print(f"OK: {len(todo)} spec(s) pass, nothing rendered (--check)")
        return
    done = {} if a.force else frozen(ws)
    overflow = []
    for n, spec, d in todo:
        if n in done:
            print(f"#{n}: skipped, {done[n]} (--force overwrites the PDF the company has)")
            continue
        out = cv_path(d, p["name"], spec["title"])
        tmp = os.path.join(d, ".rendering.pdf")  # the PDF in place stays as it was until this one fits
        r = render(p, spec, tmp)
        if r == "OVERFLOW":
            os.remove(tmp)
            overflow.append(n)
            print(f"#{n}: DOESN'T FIT: cut or shorten bullets (nothing rendered)")
            continue
        os.replace(tmp, out)
        for old in cv_pdfs(d, p["name"]):
            if old != out:
                os.remove(old)  # an earlier render under a different title
        note = ""
        if r["pages"] == 1 and r["fill"] < 0.75:
            note = f"\n   page only {r['fill']:.0%} full: add a relevant bullet or skills line (workflows/tailor.md)"
        elif r["pages"] > 1 and r["fill"] < 0.4:
            note = f"\n   last page only {r['fill']:.0%} full: cut to {r['pages'] - 1} page(s), or add content"
        print(f"#{n}: {out}{note}")
    if overflow:
        sys.exit(1)


if __name__ == "__main__":
    main()
