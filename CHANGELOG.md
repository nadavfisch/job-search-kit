# Changelog

What changed in each version, newest first. To update the kit, run `git pull` in its folder: your `my-search/`
folder stays as it is. A version that needs a change to it says so here. How versions are numbered:
[CONTRIBUTING.md](CONTRIBUTING.md#versions-and-releases).

## 1.0.0 (2026-10-06)

The first numbered version.

- **Setup** from a CV in any format (PDF, Word, text, a LinkedIn profile saved as PDF) into an approved fact base,
  `profile.yaml`, plus the user's preferences and form answers.
- **Search**: LinkedIn's public job pages, target companies' job boards (Greenhouse, Lever, Ashby, Workable,
  SmartRecruiters, Comeet), Remotive, job-alert emails, and any link. Every job is triaged apply / stretch / skip.
- **Tailored CVs**, one page by default, that `build.py` refuses to render if they say anything the profile doesn't.
  A second agent reviews each one, and `check_ready.py` runs before every submission.
- **Applying** through a browser agent, with LinkedIn pace limits (`pace.py`). Cover letters, outreach drafts and
  interview prep.
- **Tracking**: the tracker, a dated log, contacts, and `stats.py` (what's waiting, follow-ups due, which sources answer).

Fixed in this version:

- The LinkedIn search read only the first 10 jobs of each query. LinkedIn's result pages now hold 10 jobs, not 25,
  and the search stopped after any page with fewer than 20. It now pages by what each page holds, up to about
  75 jobs per query.
- When LinkedIn sends pages the kit can't read (it may have changed them), `search.py` and `fetch_jd.py` now say so,
  instead of reporting nothing, or "maybe rate-limited".

For contributors:

- Every script does its work in `main()`.
- `tests/test_live.py` reads LinkedIn's real pages, once a week in CI, and fails when the kit can't read them.
- This changelog, and [CONTRIBUTING.md](CONTRIBUTING.md).
