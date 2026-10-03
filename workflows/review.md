# Review a CV before it's sent

**When:** after every change to a job's PDF, before submitting it.
**Who:** a reviewer with a clean context, one that didn't write the CV. In Claude Code, launch a subagent
with this file as its instructions. Where there are no subagents, do it in a fresh session. The
reviewer only reports; it doesn't edit anything.
**Input:** the job folder: the PDF, `job-description.txt`, `spec.yaml`, and `cover-letter.md` if there is one. Plus `my-search/profile.yaml` and `preferences.md`.
**Output:** `review.md` in the job folder. First line: a verdict, ✅ ready / ⚠️ ready with notes / ❌ fix before sending.
Then findings by severity, each with an exact suggested rewording.

Already enforced by `kit/build.py`: invented numbers, unknown bullets, duplicates, the user's banned phrases.
The reviewer checks meaning, which code can't.

## A. Truth (any failure = ❌)
1. Every claim in the title, summary, bullets and skills is backed by profile.yaml. No tool, achievement, scope or ownership that isn't there.
2. A reworded bullet says no more than its source: no upgraded verbs (helped → led, tracked → defined), no wider scope.
3. The title doesn't claim a level the user doesn't hold and could be defended in an interview.
4. Nothing contradicts preferences.md decisions (things the user asked never to say).

## B. Fit to this job
5. The job's top 5 requirements: for each, where the CV covers it, or "gap". Never invent coverage.
6. The posting's exact keywords appear wherever they're truthful.
7. The title is close to the posting's title.
8. The summary is 3-4 lines, opens with what this job needs most, and has no clichés.
9. In each role, the first bullet is the most relevant to this job.

## C. Standards
10. ATS: the PDF reads as text in a sensible order (`python3 kit/extract_text.py <pdf>`), contact details are in the page body, section headings are standard.
11. Page count matches profile.yaml `max_pages`; body text is readable (9pt or more).
12. Bullets start with an action verb, run 1-2 lines, past tense for finished work.
13. Real numbers wherever the profile has them; no "responsible for".
14. Consistent dates, punctuation, spelling (one variety of English).
15. No repetition: the same achievement at most twice (summary + one bullet).
16. No generic AI phrasing: spearheaded, leveraged, seamlessly, cutting-edge, "not just X but Y".
17. Spelling and grammar.

## D. Cover letter (only if `cover-letter.md` exists)
18. Section A applies to every sentence of it.
19. 250-350 words, opens with what the job needs, specific to this company, no clichés, doesn't repeat the CV line by line.

## Deliberate choices (don't flag)
Anything recorded under "Decisions" in preferences.md (e.g. no education section, a fixed wording).
