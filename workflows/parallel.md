# Working with several agents

Most searches need one session. Two ways to split the work when there's more of it:

## 1. Subagents inside one session (automatic, when the agent supports them)
When several jobs need a CV at once (after a search, say), don't tailor them one by one:
- **One subagent per job** to tailor it (`workflows/tailor.md`), all in parallel. Give each one its job folder path.
- Then **one subagent per job** to review it (`workflows/review.md`). It must be a new subagent, not the one that
  wrote the CV: a writer checking its own work is a weak check.
- Triage of a big batch can also be split: one subagent per 20-30 descriptions, each returning its rows of the
  triage table; the main session merges them and writes `triage.md`.

Rules for subagents:
- A subagent writes only inside its own job folder (`spec.yaml`, the PDF, `review.md`). It never edits
  `profile.yaml`, `preferences.md`, `answers-bank.md`, `tracker.md` or `contacts.md`.
- It never asks the user anything. Questions (a fact the job needs that the profile lacks) come back in its
  report; the main session asks the user once, records the answers, and re-runs that job.
- `kit/build.py <n>` renders only job n, so parallel builds don't collide. Never run `build.py` with no numbers
  from a subagent.

## 2. Parallel sessions with roles (for heavy use)
Several agent sessions open at once, each with one job. Give each session its role in its first message
("you're the apply session, see workflows/parallel.md").

| Session | Does | Writes | Never touches |
|---|---|---|---|
| **Search** | search, triage, new job folders, tailoring + review of new jobs | `search.yaml`, `batches/`, new `jobs/` folders and their rows in the tracker | jobs that are being submitted |
| **Apply** | submits every job that passes `check_ready.py`; fixes and re-renders those CVs | the tracker rows of the jobs it submits, their folders, `answers-bank.md` | `search.yaml`, `batches/` |
| **Outreach** | contacts, messages, follow-ups, replies from the inbox | `outreach.md` / `referral-message.md` in job folders, `contacts.md` | `spec.yaml`, PDFs |

Hand-off: a job is ready for the apply session when its review is ✅ or ⚠️ (`check_ready.py` says "ready").

Shared files, safely:
- `log.md`: only through `kit/log.py`, which appends one line. Every session logs its own events.
- `tracker.md`, `preferences.md`, `profile.yaml`: change one line at a time with an exact edit, never rewrite the
  whole file, and re-read it right before editing (another session may have changed it).
- `profile.yaml` facts: only the session that's talking to the user about that fact adds it.
- Two sessions never work on the same job. If unsure, check the tracker row first.
