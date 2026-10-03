---
name: job-review
description: "Review a tailored CV before it's sent: truth, fit to the job, standards. Writes review.md. Use after any CV change and before submitting."
---

Launch a subagent (clean context, it didn't write the CV) with `workflows/review.md` as its instructions and the job folder path. It writes `review.md` in the job folder and edits nothing else. Then report the verdict and findings to the user.
