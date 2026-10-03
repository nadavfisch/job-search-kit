# The inbox: job alerts in, replies out

Needs an email tool connected to the agent (e.g. the Gmail connector in Claude, or any email MCP server).
Without one, the user forwards or pastes the emails and you do the same steps by hand.
Read only what this workflow needs: job alerts and mail from companies in the tracker. Never send, delete,
archive or label anything without the user asking.
Record the date of each check under "Decisions" in preferences.md ("inbox checked through YYYY-MM-DD"), so the
next check starts there.

## Part 1. Job alerts -> leads
Search the mail since the last check for job alerts (senders like LinkedIn Job Alerts, AllJobs, Drushim,
Indeed, Glassdoor, Wellfound, or whatever the user set up). For each job in them:
1. Skip it if it's already in tracker.md or in a batch (same link, or same company + title).
2. Open the link and get the full description (alert emails carry only a title). Can't open it: keep it as a
   lead without a description and say so; it won't be triaged until it has one.
3. Add it to today's batch:
   ```
   python3 kit/add_lead.py --batch <date> --source <alljobs|drushim|indeed|email-alert> --company "..." --title "..." --link "..." --jd - <<'EOF'
   <description>
   EOF
   ```
Then triage the batch as usual (`workflows/search.md` part 2).

## Part 2. Replies from companies
Search the mail since the last check for messages from every company with a submitted application (by company
name and domain, and the ATS senders: greenhouse, lever, ashby, workable, smartrecruiters, comeet).
Classify each one and act:
| Kind | Tracker | log.py event | Next |
|---|---|---|---|
| Rejection | Status `rejected`, Response = date | `rejected` | nothing; note any reason given |
| Interview invite / scheduling | Status `interview`, Response = date | `interview` | tell the user; offer `workflows/interview.md`; calendar (below) |
| Take-home / assessment | Response = date | `assessment` | tell the user the deadline |
| A recruiter's question or reply | Response = date | `reply` | draft an answer for the user (they send it): a draft in their mailbox if the email tool can create one, otherwise Subject + Body as copy-ready blocks |
| Auto-acknowledgement ("we got your application") | nothing | nothing | ignore |

Report: one line per company. Draft any replies; the user sends them.

## Calendar
If a calendar tool is connected and preferences.md says to use it:
- an interview: an event at the time agreed, with the job link and the path to `interview-prep.md`
- an assessment deadline: an all-day reminder
- follow-ups (only if the user asked for them): a reminder on each Follow-up date
Never invite other people or accept an invitation for the user.
