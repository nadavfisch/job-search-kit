# Tailor a CV to one job

Several jobs waiting? One subagent per job, in parallel (`workflows/parallel.md`).

Input: `my-search/jobs/NNN - Company - Role/job-description.txt`. Output: that folder's `spec.yaml` and the PDF.
Sources of truth: `profile.yaml` (facts) and `preferences.md` (decisions). Nothing else.

## 1. Read the job
- The 5 requirements the job cares about most (usually the first "you will" items and the must-haves).
- The exact keywords: tool names, the role's name, process names. ATS systems match words literally.
- For each requirement: which bullet covers it, or "gap" if none does truthfully. Don't stretch a bullet to cover a gap.

## 2. Write spec.yaml
```yaml
company: Globex
role: Operations Automation Lead
link: https://...
title: Operations Automation Lead      # close to the posting's title
summary: >
  3-4 lines. Opens with what this job needs most, backed by the user's strongest matching facts.
experience:
  - role: acme
    bullets:
      - acme_billing                   # a bullet as written in profile.yaml
      - from: acme_support             # the same facts, reworded in the job's language
        text: "Built support tooling from zero, including LLM-based ticket triage resolving 45% of tickets."
  - role: initech
    bullets: [initech_routing]
skills: [auto, ai, data]               # skills keys, or {label: ..., text: ...} for a reordered line
education: true                        # false hides the education section for this CV
```
- **Title**: the posting's title or the nearest honest one. Never a level the user doesn't hold.
- **Summary**: no clichés (passionate, results-driven, proven track record, dynamic). Every claim is in the profile.
- **Bullets**: per role, the most relevant one first. 2-4 bullets for recent roles, 1 for old ones.
  Every role in the profile stays on the CV unless the user decided otherwise (gaps raise questions).
- **Rewording** (`from:` + `text:`): use the job's words for the same facts. Shorter is fine. No new
  number, tool or scope; build.py rejects a number the source bullet doesn't have, and you must not add
  claims it can't catch (scope, ownership, seniority).
- **Skills**: put the job's tools first in each line, only tools the profile lists. A custom line may reorder
  or drop items, never add one that isn't in the profile.
- A fact the job needs that the user might have: ask them. If they confirm, add it to profile.yaml first
  (their words, their numbers), then use it.

## 3. Build
```
python3 kit/build.py --check <n>      # fix every error in the spec, then:
python3 kit/build.py <n>
```
"DOESN'T FIT": cut the weakest bullet or shorten one. Don't remove whole roles.
"page only N% full": add the next most relevant bullet (a recent role first) or a skills line. Never pad
with filler or stretch wording to fill space.

## 4. Review
Run `workflows/review.md` on it. A CV goes to the user or gets submitted only after review.
