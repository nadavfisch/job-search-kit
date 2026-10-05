"""The truth checks build.py runs before it renders anything, and the style.css rules."""

import os
import re
import unittest

from helpers import DEMO, DEMO_JOB, TEMPLATES, read

import render
from build import master_spec, new_numbers, nums, problems
from common import MAX_LETTER_SPACING, load_profile, load_yaml, style_problems


class Numbers(unittest.TestCase):
    def test_reads_numbers_the_way_cvs_write_them(self):
        cases = {
            "resolves 45% of tickets": {"45"},
            "2,000 users": {"2000"},
            "99.9% uptime": {"99.9"},
            "10K users": {"10000"},
            "saved $1.5M": {"1500000"},
            "a $2B portfolio": {"2000000000"},
            "a $1.2bn deal": {"1200000000"},
            "10 million rows": {"10000000"},
            "2018-2021": {"2018", "2021"},
            "24/7 support": {"24", "7"},
            "steps 1,2,3": {"1", "2", "3"},
        }
        for text, values in cases.items():
            with self.subTest(text):
                self.assertEqual(set(nums(text)), values)

    def test_a_unit_stuck_to_a_number_does_not_hide_it(self):
        cases = {"grew 10x": "10", "3.5x faster": "3.5", "latency down to 200ms": "200", "10TB of data": "10"}
        for text, value in cases.items():
            with self.subTest(text):
                self.assertEqual(set(nums(text)), {value})

    def test_skips_digits_inside_names(self):
        for text in ("B2B SaaS", "Web3", "H1B visa", "K8s", "EC2 and S3", "v2.0", "0-to-1"):
            with self.subTest(text):
                self.assertEqual(nums(text), {})

    def test_the_same_value_written_differently_is_the_same_number(self):
        self.assertEqual(set(nums("2,000")), set(nums("2K")))
        self.assertEqual(set(nums("2K")), set(nums("2 thousand")))
        self.assertEqual(set(nums("$1.5M")), set(nums("1.5 million")))
        self.assertNotEqual(set(nums("10K")), set(nums("10M")))

    def test_a_number_glued_to_hebrew_still_counts(self):
        self.assertEqual(set(nums("ב45% מהפניות")), {"45"})

    def test_new_numbers_are_reported_as_written(self):
        known = set(nums("from 3 days to 4 hours"))
        self.assertEqual(new_numbers("from 3 days to 2 hours, on a $2B book", known), ["2", "2B"])
        self.assertEqual(new_numbers("from 3 days to 4 hours", known), [])


class SpecChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = load_profile(DEMO)

    def errors(self, **changes):
        spec = {
            "title": "Operations Automation Lead",
            "summary": "Operations lead with 7 years automating back-office work.",
            "experience": [{"role": "acme", "bullets": ["acme_billing"]}],
            "skills": ["auto"],
        }
        spec.update(changes)
        return problems(self.p, spec)[0]

    def assertError(self, fragment, **changes):
        errors = self.errors(**changes)
        self.assertTrue(any(fragment in e for e in errors), f"no error with {fragment!r} in {errors}")

    def test_the_demo_cvs_pass(self):
        self.assertEqual(problems(self.p, load_yaml(os.path.join(DEMO, "jobs", DEMO_JOB, "spec.yaml")))[0], [])
        self.assertEqual(problems(self.p, master_spec(self.p))[0], [])
        self.assertEqual(self.errors(), [])

    def test_a_title_is_required(self):
        self.assertError("no title", title="")

    def test_free_text_is_not_a_bullet(self):
        self.assertError("is not a bullet key", experience=[{"role": "acme", "bullets": ["Did great things"]}])

    def test_a_bullet_stays_under_its_own_role(self):
        self.assertError("belongs to role 'initech'", experience=[{"role": "acme", "bullets": ["initech_routing"]}])

    def test_unknown_roles_and_bad_entries(self):
        self.assertError("unknown role 'globex'", experience=[{"role": "globex", "bullets": []}])
        self.assertError("bad experience entry 'acme'", experience=["acme"])
        self.assertError("bad bullet entry", experience=[{"role": "acme", "bullets": [{"text": "no source"}]}])

    def test_no_bullet_or_role_twice(self):
        self.assertError("used twice", experience=[{"role": "acme", "bullets": ["acme_billing", "acme_billing"]}])
        self.assertError(
            "listed twice",
            experience=[{"role": "acme", "bullets": ["acme_billing"]}, {"role": "acme", "bullets": ["acme_support"]}],
        )

    def test_one_bullet_per_overlap_group(self):
        both = [{"role": "acme", "bullets": ["acme_support", "acme_support_short"]}]
        self.assertError("overlapping", experience=both)

    def test_a_rewording_adds_no_number(self):
        for text in (
            "Built support from zero, including an LLM triage bot resolving 60% of tickets.",
            "Built support from zero, including an LLM triage bot that cut handling time 10x.",
        ):
            with self.subTest(text):
                self.assertError(
                    "adds numbers its source doesn't have",
                    experience=[{"role": "acme", "bullets": [{"from": "acme_support", "text": text}]}],
                )

    def test_a_rewording_may_keep_or_drop_numbers(self):
        for text in ("Built support tooling from zero, with LLM triage resolving 45% of tickets.", "Built support."):
            with self.subTest(text):
                reworded = [{"role": "acme", "bullets": [{"from": "acme_support", "text": text}]}]
                self.assertEqual(self.errors(experience=reworded), [])

    def test_every_number_must_be_in_the_profile(self):
        self.assertError("summary: numbers not in profile.yaml: 12", summary="Operations lead with 12 years.")
        self.assertError("title: numbers not in profile.yaml", title="Operations Lead 2030")
        self.assertError("numbers not in profile.yaml: 2024", skills=[{"label": "Tools", "text": "Tableau 2024"}])

    def test_the_users_guardrails(self):
        self.assertError("Robin isn't a developer", summary="Senior developer with 7 years.")
        self.assertError("title inflates level", title="Head of Operations")

    def test_experience_renders_in_profile_order(self):
        _, spec = problems(
            self.p,
            {
                "title": "Ops",
                "experience": [
                    {"role": "initech", "bullets": ["initech_routing"]},
                    {"role": "acme", "bullets": ["acme_billing"]},
                ],
            },
        )
        self.assertEqual([role for role, _ in spec["experience"]], ["acme", "initech"])


class StyleChecks(unittest.TestCase):
    def test_the_template_and_plain_restyling_pass(self):
        self.assertEqual(style_problems(read(os.path.join(TEMPLATES, "style.css"))), [])
        css = """@import url('https://fonts.googleapis.com/css2?family=Lato&display=block');
        :root { --text: #222; --font-body: 'Lato', Arial, sans-serif; --align-head: left; }
        h2 { border-bottom: 1.5pt solid #1f3a5f; letter-spacing: 0; font-size: 1.2em; }
        h1 { letter-spacing: .08em; } ul.edu { list-style: none; }"""
        self.assertEqual(style_problems(css), [])

    def test_refuses_what_breaks_ats_reading_or_the_page_fit(self):
        for css in (
            "ul { columns: 2 }",
            ".page { display: grid }",
            ".jh { display: flex }",
            "h1 { float: left }",
            "h1 { position: absolute }",
            "body { zoom: 1.2 }",
            "body { font-size: 12pt }",
            "h2 { background: url(logo.png) }",
            "h2 { background: linear-gradient(red, blue) }",
            "li::before { content: '>' }",
        ):
            with self.subTest(css):
                self.assertNotEqual(style_problems(css), [])

    def test_letter_spacing_stays_low_enough_for_text_extraction(self):
        for value in ("0", "0px", "normal", "-0.02em", ".05em", "0.08em", ".08em !important"):
            with self.subTest(value):
                self.assertEqual(style_problems(f"h2 {{ letter-spacing: {value} }}"), [])
        for value in (".1em", ".125em", ".25em", "0.35em", "1em", "2px", "var(--wide)"):
            with self.subTest(value):
                self.assertNotEqual(style_problems(f"h2 {{ letter-spacing: {value} }}"), [])

    def test_comments_are_ignored(self):
        self.assertEqual(style_problems("/* columns: 2; letter-spacing: 1em */ h1 { color: #123 }"), [])

    def test_the_kits_own_css_keeps_letter_spacing_low(self):
        css = render.CSS + read(os.path.join(os.path.dirname(render.__file__), "letter.py"))
        values = [float(v) for v in re.findall(r"letter-spacing:\s*([\d.]+)em", css)]
        self.assertTrue(values)
        self.assertLessEqual(max(values), MAX_LETTER_SPACING)


if __name__ == "__main__":
    unittest.main()
