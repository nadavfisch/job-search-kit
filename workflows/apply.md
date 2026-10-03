# Submit applications

## 0. Before a round
```
python3 kit/check_ready.py
```
A job that isn't "ready" isn't submitted until it's fixed. Order: newest postings with the fewest applicants first
(tracker columns Posted, Applicants). Check `preferences.md` for the approval policy: by default, show the list
(company, role, how to apply, the review verdict), open the CVs so they can look before answering
(`python3 kit/preview.py <n> <n> ...`, cover letters included), and wait for the user's OK.
With blanket approval, still open them once when a batch becomes ready, unless preferences say not to.

## 1. Per job
1. Open the posting. Still open? Not already applied (tracker "Submitted", and the page itself)?
   Closed → status `closed` in the tracker and `python3 kit/log.py closed --job N`, next job.
2. Note how to apply: LinkedIn Easy Apply, or the company's site (Greenhouse, Lever, Comeet, Workday...).
3. Fill every field from `answers-bank.md` (✅ only) and profile.yaml. Upload the job's PDF.
   A cover letter is requested: write it first (`workflows/cover-letter.md`), and have it reviewed.
4. A question with no ✅ answer: don't invent one. Close the form without sending (keep the draft if the
   site offers it), note the question, move on. Never guess salary, years, or yes/no eligibility questions.
5. Consent, privacy and terms checkboxes: only with the user's explicit OK for that checkbox.
6. Untick "Follow <company>" and newsletter boxes.
7. Submit only within the approval policy. Then confirm the page says the application was sent.
8. Tracker row: status `submitted`, Submitted = today, Follow-up = today + 7 days. Then
   `python3 kit/log.py submitted --job N --details "<how: Easy Apply / Greenhouse form / ...>"`.

## 2. After the round
Report briefly: what was submitted, what needs the user (a CAPTCHA, a login, a manual upload), and every open
question in one list. Each answer they give goes into `answers-bank.md` (✅, dated) right away.
Then offer outreach for the submitted jobs (`workflows/outreach.md`).

## Without a browser agent, or when a site blocks it
Give the user, per job: the link, the full path to the PDF, and every field's answer ready to paste.
They submit; you update the tracker when they confirm.

## Browser tips (learned the hard way)
- **Click by element reference** from the page's accessibility tree, not by coordinates from a scaled-down
  screenshot. A misclick can open "Save this application?": close it with X, never "Discard".
- **Long text** (open answers): typing drops characters. Set the value through the element's native setter
  in JS and dispatch an `input` event, then read it back and compare:
  `Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el, text); el.dispatchEvent(new Event('input',{bubbles:true}))`
- **LinkedIn Easy Apply file upload**: there's no `input[type=file]` until "Upload resume" is clicked, and the
  click opens the OS file picker. Temporarily override `HTMLInputElement.prototype.click` so a file input gets
  attached to the page instead of opening the picker, trigger "Upload resume" from JS, upload the PDF to that
  input with the browser tool's file upload, then restore the original `click`.
- **Number fields** on LinkedIn take whole numbers only (1.5 years → 2, if the user approved rounding).
- **Embedded forms** (an iframe on the careers page): open the form's own URL directly
  (e.g. Comeet: `comeet.co/jobs/<company>/<job>/apply`).
- **Company-site uploads** are often blocked for agents. Don't work around it: fill everything else and leave
  the upload and submit to the user.
