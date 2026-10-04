"""The workspace files and the scripts that keep them: tracker, log, job folders, leads, the pre-submit gate.
None of these need Chrome: the demo already has rendered PDFs."""

import datetime
import json
import os
import shutil
import time
import unittest

from helpers import DEMO_JOB, KitTest, read, write

import yaml
from common import add_tracker_row, append_row, cv_pdfs, job_dirs, letter_path, read_tracker

JD = "A real job description. " * 20  # long enough not to warn


class Tracker(KitTest):
    def test_rows_round_trip_and_cells_stay_whole(self):
        ws = self.workspace(demo=False)
        add_tracker_row(ws, {"#": 1, "Company": "Acme | Labs", "Role": "Ops\nLead", "Link": "https://x.example/1"})
        add_tracker_row(ws, {"#": 2, "Company": "Beta", "Role": "Ops", "Status": "skip"})
        rows = read_tracker(ws)
        self.assertEqual([r["#"] for r in rows], ["1", "2"])
        self.assertEqual(
            [rows[0][k] for k in ("Company", "Role", "Link")], ["Acme / Labs", "Ops Lead", "https://x.example/1"]
        )

    def test_a_missing_tracker_has_no_rows(self):
        ws = self.workspace(demo=False)
        os.remove(os.path.join(ws, "tracker.md"))
        self.assertEqual(read_tracker(ws), [])

    def test_append_row_keeps_one_line_per_row(self):
        ws = self.workspace(demo=False)
        log = os.path.join(ws, "log.md")
        append_row(log, ["2026-10-04 10:00", 1, "Acme", "note", "two\nlines | and a pipe"])
        self.assertTrue(read(log).endswith("| 2026-10-04 10:00 | 1 | Acme | note | two lines / and a pipe |\n"))


class JobFolders(KitTest):
    def test_cv_pdfs_never_include_the_cover_letter(self):
        folder = os.path.join(self.workspace(demo=False), "jobs", "001 - Acme - Ops Lead [Hybrid]")
        for name in ("Ops Lead.pdf", "Cover Letter.pdf", "Cover Letter.txt"):
            write(os.path.join(folder, f"Robin Sample - {name}"), "")
        write(os.path.join(folder, "notes.pdf"), "")
        found = [os.path.basename(f) for f in cv_pdfs(folder, "Robin Sample")]
        self.assertEqual(found, ["Robin Sample - Ops Lead.pdf"])
        self.assertEqual(os.path.basename(letter_path(folder, "Robin Sample")), "Robin Sample - Cover Letter.pdf")

    def test_job_dirs_reads_the_number_off_each_folder(self):
        ws = self.workspace()
        os.makedirs(os.path.join(ws, "jobs", "012 - Beta - Ops [Remote]"))
        os.makedirs(os.path.join(ws, "jobs", "not a job"))
        self.assertEqual(sorted(job_dirs(ws)), [1, 12])


class NewJob(KitTest):
    LINK = "https://jobs.example.com/1?ref=a#apply"  # a "#" that YAML mustn't take for a comment

    def new_job(self, ws, *args):
        return self.kit("new_job.py", "--company", "Acme", "--role", "Ops Lead", "--jd", "-", *args, ws=ws, stdin=JD)

    def test_opens_the_folder_and_records_it(self):
        ws = self.workspace(demo=False)
        folder = self.assertOK(self.new_job(ws, "--link", self.LINK)).strip()
        self.assertEqual(os.path.basename(folder), "001 - Acme - Ops Lead")
        self.assertEqual(read(os.path.join(folder, "job-description.txt")), JD)
        spec = yaml.safe_load(read(os.path.join(folder, "spec.yaml")))
        self.assertEqual([spec[k] for k in ("company", "role", "link")], ["Acme", "Ops Lead", self.LINK])
        self.assertIsNone(spec["title"])
        row = read_tracker(ws)[-1]
        self.assertEqual((row["#"], row["Company"], row["Status"]), ("1", "Acme", "apply"))
        self.assertIn("| 1 | Acme | added | Ops Lead (manual, apply) |", read(os.path.join(ws, "log.md")))

    def test_refuses_a_tracked_link_but_not_a_longer_one(self):
        ws = self.workspace(demo=False)
        self.assertOK(self.new_job(ws, "--link", "https://jobs.example.com/12"))
        self.assertOK(self.new_job(ws, "--link", "https://jobs.example.com/1"))
        again = self.new_job(ws, "--link", "https://jobs.example.com/1/")
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("Already in the tracker", again.stderr)
        self.assertEqual(len(read_tracker(ws)), 2)

    def test_a_job_from_a_batch_lead(self):
        ws = self.workspace(demo=False)
        args = "--batch 2026-10-04 --source alljobs --company Beta --title BizOps --link https://beta.example/7 --jd -"
        lead = self.kit("add_lead.py", *args.split(), ws=ws, stdin=JD)
        jid = self.assertOK(lead).strip()
        self.assertTrue(jid.startswith("lead-"))
        folder = self.assertOK(self.kit("new_job.py", "--batch", "2026-10-04", "--id", jid, ws=ws)).strip()
        self.assertEqual(os.path.basename(folder), "001 - Beta - BizOps")
        row = read_tracker(ws)[-1]
        self.assertEqual((row["Source"], row["Link"]), ("alljobs", "https://beta.example/7"))


class AddLead(KitTest):
    def test_a_wrong_description_path_leaves_no_half_lead(self):
        ws = self.workspace(demo=False)
        args = "--batch 2026-10-04 --source manual --company C --title T --link https://c.example/1".split()
        failed = self.kit("add_lead.py", *args, "--jd", os.path.join(ws, "missing.txt"), ws=ws)
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(ws, "batches", "2026-10-04", "jobs_all.json")))
        self.assertOK(self.kit("add_lead.py", *args, "--jd", "-", ws=ws, stdin=JD))
        again = self.kit("add_lead.py", *args, ws=ws)
        self.assertIn("already in batch", again.stderr)


class BuildArguments(KitTest):
    def test_a_mistyped_argument_builds_nothing(self):
        result = self.kit("build.py", "mastr", ws=self.workspace())
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a job number or 'master': mastr", result.stderr)

    def test_check_only(self):
        result = self.kit("build.py", "--check", "1", "master", ws=self.workspace())
        self.assertIn("OK: 2 spec(s) pass", self.assertOK(result))

    def test_a_failing_spec_stops_the_build(self):
        ws = self.workspace()
        spec = os.path.join(ws, "jobs", DEMO_JOB, "spec.yaml")
        write(spec, read(spec).replace("Operations lead with 7 years", "Operations lead with 12 years"))
        result = self.kit("build.py", "1", ws=ws)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("summary: numbers not in profile.yaml: 12", result.stderr)

    def test_the_style_check_runs_before_anything(self):
        ws = self.workspace()
        write(os.path.join(ws, "style.css"), "h2 { letter-spacing: .2em }")
        result = self.kit("build.py", "--check", "master", ws=ws)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("style.css isn't allowed to use: letter-spacing", result.stderr)


class LogStatsPace(KitTest):
    def log(self, ws, *rows):
        for when, job, event, details in rows:
            append_row(os.path.join(ws, "log.md"), [when, job, "Acme", event, details])

    def test_log_takes_known_events_only(self):
        ws = self.workspace()
        self.assertOK(self.kit("log.py", "submitted", "--job", "1", "--details", "Greenhouse form", ws=ws))
        self.assertIn("| 1 | Globex | submitted | Greenhouse form |", read(os.path.join(ws, "log.md")))
        self.assertNotEqual(self.kit("log.py", "applied", ws=ws).returncode, 0)

    def test_stats_counts_what_was_sent_and_what_answered(self):
        ws = self.workspace(demo=False)
        today = datetime.date.today()
        old = (today - datetime.timedelta(days=30)).isoformat()
        sent = {"Source": "linkedin", "Submitted": old}
        add_tracker_row(ws, {"#": 1, "Company": "Acme", "Status": "interview", **sent})
        add_tracker_row(ws, {"#": 2, "Company": "Beta", "Status": "submitted", "Follow-up": old, **sent})
        add_tracker_row(ws, {"#": 3, "Company": "Gamma", "Source": "greenhouse", "Status": "apply"})
        self.log(ws, (f"{today} 09:00", 1, "interview", "first round"))
        out = self.assertOK(self.kit("stats.py", ws=ws))
        self.assertIn("Submitted 2 · responded 1 (50%) · interviews 1 (50%)", out)
        self.assertIn("| linkedin | 2 | 1 (50%) | 1 (50%) |", out)
        for section in ("Waiting to submit (1)", "Follow-ups due (1)", "No answer for 3+ weeks (1)"):
            self.assertIn(section, out)
        self.assertIn("Last 7 days: interview 1", out)

    def test_pace_ok_wait_and_stop(self):
        now = datetime.datetime.now()
        if now.hour == 0 and now.minute < 20:
            self.skipTest("the test's submissions would straddle midnight")
        ws = self.workspace(demo=False)

        def stamp(minutes_ago):
            return (now - datetime.timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M")

        self.assertIn("OK: 0/15 today", self.assertOK(self.kit("pace.py", ws=ws)))
        self.log(ws, (stamp(1), 1, "submitted", "LinkedIn Easy Apply"))
        self.assertRegex(self.kit("pace.py", ws=ws).stderr, r"^WAIT [12] min: 1/15 today")
        self.assertIn("OK: 1/15 today", self.assertOK(self.kit("pace.py", "--gap", "1", ws=ws)))
        self.log(ws, (stamp(1), 2, "submitted", "Greenhouse form"))  # not LinkedIn: doesn't count
        self.assertIn("OK: 1/15 today", self.assertOK(self.kit("pace.py", "--gap", "1", ws=ws)))
        self.log(ws, *[(stamp(10 + i), 3 + i, "submitted", "linkedin easy apply") for i in range(4)])
        self.assertIn("WAIT: 5/15 today, 5/5 this hour", self.kit("pace.py", ws=ws).stderr)
        self.assertIn("STOP for today", self.kit("pace.py", "--per-day", "5", ws=ws).stderr)


class CheckReady(KitTest):
    def setUp(self):
        self.ws = self.workspace()
        self.job = os.path.join(self.ws, "jobs", DEMO_JOB)
        self.spec = os.path.join(self.job, "spec.yaml")
        self.review = os.path.join(self.job, "review.md")

    def check(self, *args):
        return self.kit("check_ready.py", *args, ws=self.ws)

    def write_review(self, text):
        write(self.review, text)
        later = time.time() + 5  # newer than the PDF, whatever the copy did to the times
        os.utime(self.review, (later, later))

    def test_ready_once_reviewed(self):
        self.assertIn("no review.md", self.check().stdout)
        self.write_review("Verdict: ⚠ ready with notes\n\n- ❌ was: a wider scope (fixed)\n")
        self.assertIn("#1 Globex: ready (review ⚠)", self.assertOK(self.check()))

    def test_a_failed_review_blocks(self):
        self.write_review("❌ fix before sending\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("review verdict ❌", result.stdout)

    def test_a_pdf_newer_than_its_review(self):
        self.write_review("✅ ready\n")
        pdf = os.path.join(self.job, "Robin Sample - Operations Automation Lead.pdf")
        later = time.time() + 60
        os.utime(pdf, (later, later))
        self.assertIn("PDF changed after the review", self.check().stdout)

    def test_a_spec_changed_after_the_render(self):
        self.write_review("✅ ready\n")
        write(self.spec, read(self.spec).replace("title: Operations Automation Lead", "title: Automation Lead"))
        self.assertIn("no PDF for the current title (run kit/build.py 1)", self.check().stdout)
        write(self.spec, read(self.spec).replace("title: Automation Lead", "title: Operations Automation Lead"))
        write(self.spec, read(self.spec).replace("using Zapier, Make", "using Make"))
        self.assertIn("PDF doesn't match spec.yaml", self.check().stdout)

    def test_the_cover_letter_is_not_taken_for_the_cv(self):
        self.write_review("✅ ready\n")
        other_pdf = os.path.join(self.ws, "master", "Robin Sample - Operations & Automation Lead.pdf")
        shutil.copy(other_pdf, letter_path(self.job, "Robin Sample"))
        self.assertIn("ready (review ✅)", self.assertOK(self.check()))

    def test_job_numbers_not_in_the_tracker(self):
        self.write_review("✅ ready\n")
        result = self.check("1", "7")
        self.assertEqual(result.returncode, 1)
        self.assertIn("#7: not in tracker.md", result.stdout)


class Batches(KitTest):
    def test_fetch_jd_needs_an_existing_batch(self):
        result = self.kit("fetch_jd.py", "2020-01-01", "new", ws=self.workspace())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No batch at", result.stderr)

    def test_search_refuses_an_unknown_source(self):
        result = self.kit("search.py", "--only", "linkdin", ws=self.workspace())
        self.assertEqual(result.returncode, 2)
        self.assertIn("--only takes linkedin, companies, remote", result.stderr)

    def test_jobs_all_is_plain_json(self):
        ws = self.workspace(demo=False)
        args = "--batch b1 --source manual --company Café --title T --link https://c.example/1".split()
        jid = self.assertOK(self.kit("add_lead.py", *args, ws=ws)).strip()
        jobs = json.loads(read(os.path.join(ws, "batches", "b1", "jobs_all.json")))
        self.assertEqual(jobs[jid]["company"], "Café")


if __name__ == "__main__":
    unittest.main()
