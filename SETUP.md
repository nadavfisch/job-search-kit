# Setup (first run)

Goal: in about 15 minutes, turn the user's existing CV into an approved fact base, learn what they're
looking for, and show them their first CV built by the kit. Talk in the user's language. Ask a few
questions at a time, never a wall of them.

## 1. Check the machine
```
python3 --version                               # 3.9 or newer
python3 -m pip install -r requirements.txt      # pypdf, pyyaml
python3 kit/render.py --check                   # needs Google Chrome, Chromium or Edge
```
If something is missing, say what to install, in one line each. Don't continue until `render.py --check` says OK.

## 2. Create the workspace
```
mkdir -p my-search/source-cv my-search/jobs my-search/batches
cp templates/profile.yaml templates/preferences.md templates/answers-bank.md templates/tracker.md templates/search.yaml \
   templates/log.md templates/contacts.md my-search/
```
If `my-search/` already exists, don't overwrite anything. Ask whether to continue the existing setup.

## 3. Get the CV
Ask for their CV: a file path, or drag the file into the chat. Any format works: PDF, Word (.docx),
text, a LinkedIn profile saved as PDF (LinkedIn: More > Save to PDF). More than one version is better:
each extra source adds bullets to choose from. Copy each file into `my-search/source-cv/`, then:
```
python3 kit/extract_text.py my-search/source-cv/<file>
```
A scanned PDF gives no text: read it as an image, or ask for another format.

## 4. Build profile.yaml
From the sources only:
- **contact, links, name**, as written.
- **experience**: one entry per role, newest first. `header` = "Role | Company - short description | years".
  `bullets` = every achievement, each under a short key (`<role>_<topic>`), close to the original wording.
  Clean up grammar; don't add facts. When two sources describe the same thing, keep the stronger version and,
  if both are useful (long and short), list both and put them in one `rules.overlaps` group.
- **skills**: 3-5 lines grouped by theme, from tools the sources mention.
- **summary / headline**: from the CV; mark it as a draft for the user to approve.

Then list what's unclear and ask (a few at a time): numbers without context, dates that don't line up,
gaps, a vague claim ("improved efficiency": by how much? any number they can stand behind?). Write each
confirmed answer into the profile. Never fill a gap with a guess.

## 5. What they're looking for
Ask, and write the answers into `preferences.md` and `answers-bank.md`:
1. Which roles? Which seniority? Any titles they'd never take?
2. Where: city, remote, hybrid, relocation? Work authorization / visa?
3. Salary expectations (the number they'd put on a form) and availability / notice period.
4. Industries they want, and ones to avoid. Hard deal-breakers?
5. Anything that must never appear on their CV, or that misrepresents them (e.g. "don't call me a developer").
   This goes into `rules.banned` in profile.yaml. Levels they don't hold go into `rules.title_banned`.
6. Submission approval: ask before each application (default), or apply to every approved match without asking?
7. Is anyone at a target company who could refer them? Those jobs become "referral" instead of a cold application.
8. The CV's language and direction (for Hebrew or Arabic: `rtl: true` and Hebrew `labels` in profile.yaml).
9. Which companies would they most like to work at? (Up to 20-30. These get checked directly, see step 7.)
10. Tools: if an email or calendar tool is connected to you, ask whether to use it: email to pick up job alerts
    and replies from companies (read only), calendar for interviews and follow-up reminders. Record the answer
    under "Decisions". Not connected: mention once that connecting one (e.g. Gmail and Google Calendar in Claude's
    connector settings) lets you track replies automatically; it's optional.

Fill the short-field table in `answers-bank.md` from these answers and the profile, marked ✅.

## 6. The first CV
```
python3 kit/build.py master
```
Open `my-search/master/*.pdf` (or tell them where it is). Ask what's wrong or missing. Fix the profile
(the facts), rebuild, repeat until they're happy. This also confirms the summary and headline.
If the result doesn't fit on one page: drop bullets from `default`, or set `max_pages: 2` if they want two.

## 7. Search settings
Write `my-search/search.yaml`:
- `linkedin`: location (and `geo_id` if known) and 10-30 queries made from their target roles, the tools
  they're strongest in, and common title variants.
- `companies`: for each target company, `python3 kit/sources.py guess "<name>"`; no luck, find its careers page
  (web search or browser) and `python3 kit/sources.py detect <url>`. Add what's found. Companies that use neither
  (a custom careers site) go under "Decisions" as "check by hand: <company> <careers url>".
  Set `title_keywords` (short words from their target titles), `title_exclude`, and `locations`.
- `remote`: only if they want remote work: queries and the regions they can work from.
- Email alerts: if they use email, suggest they set job alerts on the job sites they like (for Israel: AllJobs,
  Drushim; elsewhere: Indeed, Glassdoor, Wellfound) and on LinkedIn. `workflows/inbox.md` reads them.
Run `python3 kit/search.py --only companies,remote` once to confirm the companies resolve.
Tell them once, plainly: the search reads LinkedIn's public job pages and applying uses their own browser,
and LinkedIn's terms forbid automation, so volumes stay low and the risk is theirs.

## 8. Done
Record the setup date under "Decisions" in preferences.md. Then tell them what they can ask for next:
- "find me jobs": search, triage, and tailored CVs for the matches
- "apply to this job: <link or pasted text>"
- "what's waiting?": status, follow-ups due, and what's working (kit/stats.py)
- "check my email": new job alerts and replies from companies (if email is connected)
And that next time, they should open the agent in this folder so it picks up where it left off.
