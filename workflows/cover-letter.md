# Write a cover letter

When: a form asks for one (a file or a text box), or the user asks. Not by default: most applications don't need it.
Same rule as the CV: every claim comes from profile.yaml or something the user told you and you wrote down.

## Write `cover-letter.md` in the job folder
250-350 words, in the posting's language, plain paragraphs separated by blank lines, each paragraph on one line
(a line break inside a paragraph is kept, as in the sign-off: "Best," then the name on the next line):
1. **Opening (2-3 sentences)**: the role, and the one thing this job needs most that the user has done.
   Something specific to this company if there's something real (their product, a recent launch from the
   description or their site). No "I am writing to apply for...", no "I am thrilled".
2. **Proof (1-2 short paragraphs)**: the 2-3 profile achievements that match the job's top requirements,
   with their real numbers. Use the posting's words where they're truthful.
3. **A gap, if there's an obvious one** (optional, one sentence): what they have that's adjacent.
4. **Close (1-2 sentences)**: a plain ask to talk. Sign-off with the user's name.

No clichés (passionate, results-driven, proven track record, team player), no repeating the CV line by line,
no flattery. The greeting: "Dear <name>," if the hiring manager is known, otherwise "Dear <Company> team,".

## Check and render
```
python3 kit/letter.py <n> --check     # numbers must be in profile.yaml; banned phrases; length
python3 kit/letter.py <n>             # -> <Name> - Cover Letter.pdf in the job folder
```
Give the user the PDF (and the text as `<Name> - Cover Letter.txt` for text boxes), never the .md: most forms only
take PDF/DOCX, and markdown symbols end up in pasted text. For a text box you fill yourself, paste the plain text
(through JS for long text, see apply.md).
The letter is part of the review: when `review.md` is written after the letter exists, it covers the letter too.
