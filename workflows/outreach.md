# Reach out after applying, and follow up

The agent finds people and drafts messages. **The user sends every message themselves.** Never send, connect,
or click "Send" on their behalf; at most, prepare the note inside the site and stop.

## 1. Who to contact (after a job is submitted)
Check `my-search/contacts.md` first: someone already contacted at this company is the first person to
write to again, and nobody gets a second cold note.
Using the browser (LinkedIn people search, the company site), find up to 3 people:
the likely hiring manager (the team the job sits in), a team member, a recruiter for that team.
Mark the best one ⭐. Prefer people who are active (recent posts) and any mutual connections.

## 2. outreach.md in the job folder
For each person:
- name, role, profile link
- **why them**, in one line (and how sure you are: "probably the hiring manager, not verified")
- **mutual connections**, if any: a warm intro beats a cold message, so ask the user if they know one
- **hook**: something real and recent from their posts or the company's news
- **message** in the person's language. Connection notes are short (LinkedIn: 200 characters; free accounts
  get only a few personalized notes a month, so only the ⭐ person gets one). Count characters in code, not by eye.

Add each person to `my-search/contacts.md` with status `drafted`. When the user says they sent it: status
`sent`, Last contact = today, and `python3 kit/log.py message-sent --job N --details "<name>, <channel>"`.
When someone answers: status `replied`, and log `reply`.

A good note: what they applied for, one fact from the CV that matches what the team needs, the hook, a light ask.
No flattery, no "I'd love to pick your brain", no attachments.

## 3. Follow-up (a week after submitting)
For each tracker row whose Follow-up date is today or past, with no Response:
draft a short follow-up (to the ⭐ contact if connected, or the recruiter) in `outreach.md`, and list them for the user
(`python3 kit/stats.py` lists every follow-up that's due). Once sent: `kit/log.py follow-up-sent`, and update contacts.md.
When they hear back, update the Response column (and Status: interview / rejected), and log it.
If the user wants reminders in their calendar, see the Calendar section of `workflows/inbox.md`.

## Referrals
A job where the user knows someone: no cold application. Draft `referral-message.md`: a short, friendly ask,
the job link, and 2-3 lines the contact can forward as-is.
