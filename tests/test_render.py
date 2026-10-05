"""End to end through Chrome: build the CVs and the cover letter, then read the PDFs back like an ATS would.
Skipped when no Chrome, Chromium or Edge is found (set CHROME_PATH to point at one)."""

import os
import shutil
import subprocess
import time
import unittest

from helpers import DEMO_JOB, KitTest, read, write

import pypdf
import yaml
from common import cv_pdfs, letter_path
from render import find_chrome

NAME = "Robin Sample"
CV = f"{NAME} - Operations Automation Lead.pdf"
LETTER = """Dear Globex team,

At Acme Analytics I automated billing and collections end to end, cutting the monthly close from 3 days to 4 hours.

Best,
Robin Sample
"""


def text_of(pdf):
    return "\n".join(page.extract_text() for page in pypdf.PdfReader(pdf).pages)


@unittest.skipUnless(find_chrome(), "needs Chrome, Chromium or Edge (or CHROME_PATH)")
class Render(KitTest):
    def setUp(self):
        self.ws = self.workspace()
        self.job = os.path.join(self.ws, "jobs", DEMO_JOB)
        for pdf in cv_pdfs(self.job, NAME) + cv_pdfs(os.path.join(self.ws, "master"), NAME):
            os.remove(pdf)  # render from scratch, not the committed copies

    def build(self, *args):
        return self.kit("build.py", *args, ws=self.ws)

    def test_the_demo_cvs_fit_one_page_and_read_back_as_text(self):
        out = self.assertOK(self.build("1", "master"))
        self.assertNotIn("DOESN'T FIT", out)
        for pdf in (
            os.path.join(self.job, CV),
            os.path.join(self.ws, "master", f"{NAME} - Operations & Automation Lead.pdf"),
        ):
            with self.subTest(os.path.basename(pdf)):
                self.assertEqual(len(pypdf.PdfReader(pdf).pages), 1)
                text = text_of(pdf)
                for line in ("ROBIN SAMPLE", "WORK EXPERIENCE", "EDUCATION", "SKILLS", "robin@example.com"):
                    self.assertIn(line, text)

    @unittest.skipUnless(shutil.which("pdftotext"), "needs pdftotext (poppler)")
    def test_section_headings_extract_as_whole_words(self):
        self.assertOK(self.build("1"))
        text = subprocess.run(
            ["pdftotext", "-layout", os.path.join(self.job, CV), "-"], capture_output=True, text=True
        ).stdout
        for heading in ("WORK EXPERIENCE", "EDUCATION", "SKILLS", "LANGUAGES"):
            self.assertIn(heading, text)

    def test_the_cover_letter_survives_a_cv_rebuild(self):
        write(os.path.join(self.job, "cover-letter.md"), LETTER)
        self.assertIn("OK: ", self.assertOK(self.kit("letter.py", "1", "--check", ws=self.ws)))
        self.assertOK(self.kit("letter.py", "1", ws=self.ws))
        self.assertOK(self.build("1"))
        self.assertTrue(os.path.exists(letter_path(self.job, NAME)))
        self.assertEqual(read(letter_path(self.job, NAME, ".txt")), LETTER.strip() + "\n")
        letter = text_of(letter_path(self.job, NAME))
        self.assertIn("monthly close from 3 days to 4 hours", " ".join(letter.split()))
        self.assertIn("Best,\nRobin Sample", letter)  # the sign-off keeps its line break
        write(os.path.join(self.job, "review.md"), "✅ ready\n")
        later = time.time() + 5
        os.utime(os.path.join(self.job, "review.md"), (later, later))
        self.assertIn("#1 Globex: ready (review ✅)", self.assertOK(self.kit("check_ready.py", ws=self.ws)))

    def test_the_letter_gets_the_same_truth_checks(self):
        write(os.path.join(self.job, "cover-letter.md"), LETTER.replace("4 hours", "2 hours"))
        result = self.kit("letter.py", "1", ws=self.ws)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("numbers not in profile.yaml: 2", result.stderr)
        self.assertFalse(os.path.exists(letter_path(self.job, NAME)))

    def test_a_new_title_replaces_the_old_pdf(self):
        jd = "A real job description. " * 20
        folder = self.assertOK(
            self.kit(
                "new_job.py", "--company", "Acme", "--role", "Ops Lead [Hybrid]", "--jd", "-", ws=self.ws, stdin=jd
            )
        ).strip()
        spec = {"title": "Operations Lead", "summary": "Operations lead with 7 years.", "skills": ["auto"],
                "experience": [{"role": "acme", "bullets": ["acme_billing"]}]}  # fmt: skip
        write(os.path.join(folder, "spec.yaml"), yaml.safe_dump(spec))
        self.assertOK(self.build("2"))
        spec["title"] = "Operations Lead (Hybrid)"
        write(os.path.join(folder, "spec.yaml"), yaml.safe_dump(spec))
        self.assertOK(self.build("2"))
        self.assertEqual(
            [os.path.basename(p) for p in cv_pdfs(folder, NAME)], [f"{NAME} - Operations Lead (Hybrid).pdf"]
        )

    def test_a_cv_that_does_not_fit_renders_nothing(self):
        profile = yaml.safe_load(read(os.path.join(self.ws, "profile.yaml")))
        long = profile["experience"][0]["bullets"]["acme_billing"] + " For every region, product and team."
        profile["experience"][0]["bullets"].update({f"acme_more{i}": long for i in range(40)})
        write(os.path.join(self.ws, "profile.yaml"), yaml.safe_dump(profile, allow_unicode=True, sort_keys=False))
        spec = yaml.safe_load(read(os.path.join(self.job, "spec.yaml")))
        spec["experience"][0]["bullets"] += [f"acme_more{i}" for i in range(40)]
        write(os.path.join(self.job, "spec.yaml"), yaml.safe_dump(spec))
        result = self.build("1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("DOESN'T FIT", result.stdout)
        self.assertEqual([f for f in os.listdir(self.job) if f.endswith(".pdf")], [])  # no CV, no half-rendered file

    def test_a_submitted_pdf_is_never_overwritten(self):
        self.assertOK(self.build("1"))
        pdf = os.path.join(self.job, CV)
        stamp = os.path.getmtime(pdf)
        tracker = os.path.join(self.ws, "tracker.md")
        write(tracker, read(tracker).replace("| apply | |", "| submitted | 2026-10-02 |"))
        self.assertIn("skipped, submitted 2026-10-02", self.assertOK(self.build("1")))
        self.assertEqual(os.path.getmtime(pdf), stamp)
        self.assertOK(self.build("1", "--force"))
        self.assertGreater(os.path.getmtime(pdf), stamp)


if __name__ == "__main__":
    unittest.main()
