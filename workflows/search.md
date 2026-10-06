# Find jobs and triage them

Read `my-search/preferences.md` first: target roles, deal-breakers and triage rules decide everything here.

## 1. Collect
```
python3 kit/search.py                 # every source in search.yaml -> batches/<today>/
python3 kit/fetch_jd.py <date> new    # LinkedIn descriptions (other sources already saved theirs)
```
Sources (all optional, set in `my-search/search.yaml`):
- **LinkedIn** public search. If nothing comes back, LinkedIn is rate-limiting: wait, don't retry in a loop.
  If it says LinkedIn may have changed its pages, tell the user the kit needs an update (`git pull`); the other
  sources still work meanwhile.
- **Target companies**: their own job boards (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Comeet),
  filtered by title keywords and locations. To add a company:
  `python3 kit/sources.py guess "<name>"`, or find its careers page and `python3 kit/sources.py detect <url>`.
  Neither works (a custom careers site)? Check that company in the browser once per search and add matches
  with `kit/add_lead.py`.
- **Remote boards** (Remotive), for remote searches.
- **Email alerts**: if the user gets job alerts by email (AllJobs, Drushim, Indeed, LinkedIn, Glassdoor...),
  run `workflows/inbox.md` part 1. It adds them to the same batch.
- **Anything else** (a friend's tip, a job site the user browses): `python3 kit/add_lead.py`.

## 2. Triage
For every new job in the batch (`new: true` in jobs_all.json) with a description in `jd/<id>.txt`:
- **Company**: only from the description itself. Never guess from the title or a similar company.
- **Empty or very short description**: open the link and get it, or skip with "no description". Never triage a title.
- **Already in tracker.md** (same link, or same company + title): skip.
- **Fit 1-10** against the profile and preferences, then one decision:
  - `apply`: real fit, requirements met or loosely worded
  - `stretch`: worth a shot, one clear gap
  - `referral`: the user knows someone there (see preferences and contacts.md)
  - `skip`: one short reason (a preferences auto-skip rule, a core skill they don't have, wrong domain, too senior)
- **Why**: one sentence, specific to this job and this person.

Write `batches/<date>/triage.md`: one table of apply/stretch/referral ranked by fit
(# · Fit · Decision · Company · Title · Location · Source · Applicants · Why · Link), then a short skip table
(Company · Title · Reason).

## 3. Show the user
Short summary in their language: how many found per source, how many matches, the match table, and the skip
reasons grouped ("12 skipped: too senior"). Ask them to approve, change decisions, or add jobs. When they
change a decision, ask why if it reveals a rule, and add the rule to preferences.md.

## 4. Open job folders
For each approved apply/stretch/referral job, in order of fit:
```
python3 kit/new_job.py --batch <date> --id <id> --status apply
```
Then tailor each one (`workflows/tailor.md`) and review it (`workflows/review.md`).
Referral jobs: no application. Draft a short message to the contact asking for a referral, in
`jobs/NNN/referral-message.md`.

## A single job
The user pastes a link or the text of a job. Get the full description (open the link in the browser, or use
the pasted text; if neither works, ask them to paste it), then:
```
python3 kit/new_job.py --company "<from the posting>" --role "<title>" --link "<url>" --source manual --jd - --status apply <<'EOF'
<full description>
EOF
```
Give a quick fit read first (2-3 lines: strengths, gaps, apply or not). Then tailor.
