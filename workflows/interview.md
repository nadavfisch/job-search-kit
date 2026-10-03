# Prepare for an interview

No new facts here either: every story comes from profile.yaml, preferences.md, or what the user tells you now.
Where a real detail is missing, write **[fill in]**. The user fills it in, not the agent.

## When an interview is scheduled
Tracker status `interview`, `python3 kit/log.py interview --job N --details "<round, date, with whom>"`, and a
calendar event if the user uses one (see `workflows/inbox.md`). Then create `interview-prep.md` in the job folder:
1. **The CV they saw**: the PDF in the job folder is the version that was sent (build.py doesn't overwrite
   submitted ones). Rule: say nothing in the interview that the CV doesn't support, and nothing that contradicts it.
2. **What the job needs**: the top 5 requirements from `job-description.txt`, and the gaps from `review.md`.
3. **Likely questions**: for each requirement, which story answers it. For each gap, an honest answer
   (what they have that's adjacent, how fast they'd close it, a concrete example of learning something fast).
4. **Research**: what the company does, its stage, recent news, who the interviewer is. If `outreach.md`
   exists, the hooks are already there.
5. **3 questions to ask them**: e.g. what success looks like at 90 days, which processes are most manual today.
6. **After the interview**: what they asked, what landed, what didn't (log it as a `note`). Feedback that applies elsewhere goes
   into `my-search/interview-bank.md`.

## my-search/interview-bank.md (shared across interviews)
- **Hard questions, locked answers**: why they left their last job, gaps, missing degree, salary. Agree on the
  wording once with the user, mark it locked, and reuse it word for word. List the things that must never be
  said next to each one.
- **Stories (STAR)**: 6-8 stories from the profile's strongest bullets: situation, task, action, result, with
  the profile's numbers only. Each tagged with the questions it answers (conflict, failure, ownership, ambiguity, impact).
