"""Job sources, offline: each job board's API answer is faked, the parsing and the search filters are real."""

import contextlib
import datetime
import io
import json
import os
import runpy
import sys
import unittest
from unittest import mock

from helpers import KIT, KitTest, read, write

import sources

TODAY = datetime.datetime.now(datetime.timezone.utc)
RECENT, OLD = TODAY.date().isoformat(), (TODAY - datetime.timedelta(days=30)).date().isoformat()

API = {  # url fragment -> the board's answer
    "boards-api.greenhouse.io/v1/boards/acme/": {
        "jobs": [
            {"id": 1, "title": "Operations Lead", "location": {"name": "Tel Aviv"}, "first_published": RECENT,
             "absolute_url": "https://boards.greenhouse.io/acme/jobs/1", "content": "&lt;p&gt;Own &amp;amp; automate ops&lt;/p&gt;"},
            {"id": 2, "title": "Operations Intern", "location": {"name": "Tel Aviv"}, "first_published": RECENT,
             "absolute_url": "https://boards.greenhouse.io/acme/jobs/2", "content": ""},
            {"id": 3, "title": "Automation Engineer", "location": {"name": "Berlin"}, "first_published": RECENT,
             "absolute_url": "https://boards.greenhouse.io/acme/jobs/3", "content": ""},
            {"id": 4, "title": "Business Operations Manager", "location": {"name": "Tel Aviv"}, "first_published": OLD,
             "absolute_url": "https://boards.greenhouse.io/acme/jobs/4", "content": ""},
            {"id": 5, "title": "Retail Associate", "location": {"name": "Tel Aviv"}, "first_published": RECENT,
             "absolute_url": "https://boards.greenhouse.io/acme/jobs/5", "content": ""},
        ]
    },
    "api.lever.co/v0/postings/beta": [
        {"id": "b1", "text": "Ops Automation Lead", "categories": {"location": None}, "workplaceType": "remote",
         "createdAt": TODAY.timestamp() * 1000, "hostedUrl": "https://jobs.lever.co/beta/b1",
         "descriptionPlain": "Run ops.", "lists": [{"text": "You will", "content": "<li>Automate billing</li>"}]},
    ],
    "api.ashbyhq.com/posting-api/job-board/gamma": {
        "jobs": [
            {"id": "g1", "title": "Operations Analyst", "location": "Tel Aviv", "isRemote": False,
             "publishedAt": RECENT, "jobUrl": "https://jobs.ashbyhq.com/gamma/g1", "descriptionPlain": "Analyze."},
            {"id": "g2", "title": "Operations Lead", "isListed": False, "jobUrl": "x"},
        ]
    },
    "apply.workable.com/api/v1/widget/accounts/delta": {
        "name": "Delta Ltd",
        "jobs": [{"shortcode": "D1", "title": "Ops Manager", "city": "Haifa", "country": "Israel", "telecommuting": True,
                  "published_on": RECENT, "url": "https://apply.workable.com/delta/j/D1", "description": "<p>Lead ops</p>"}],
    },
    "api.smartrecruiters.com/v1/companies/Eps/postings?": {
        "totalFound": 1,
        "content": [{"id": "e1", "name": "Operations Lead", "location": {"fullLocation": "Tel Aviv, Israel"},
                     "releasedDate": RECENT, "company": {"name": "Eps"}}],
    },
    "api.smartrecruiters.com/v1/companies/Eps/postings/e1": {
        "jobAd": {"sections": {"jobDescription": {"title": "The job", "text": "<p>Run it</p>"}, "other": {"text": ""}}}
    },
    "comeet.co/careers-api/2.0/company/A1.B2C/positions": [
        {"uid": "C1", "name": "Operations Lead", "location": {"name": "Tel Aviv", "is_remote": False},
         "time_updated": RECENT, "url_active_page": "https://www.comeet.com/jobs/zeta/A1.B2C/ops/C1",
         "details": [{"name": "Description", "value": "<p>Do it</p>"}]},
    ],
    "remotive.com/api/remote-jobs": {
        "jobs": [{"id": 9, "title": "Remote Operations Lead", "company_name": "Rho", "candidate_required_location": "Worldwide",
                  "publication_date": RECENT, "url": "https://remotive.com/9", "description": "<p>Anywhere</p>"}]
    },
}  # fmt: skip
PAGES = {"https://www.comeet.com/jobs/zeta/A1.B2C": 'window.x = {"token": "0123456789ABCDEF0123"};'}


def fake_get_json(url):
    for fragment, answer in API.items():
        if fragment in url:
            return json.loads(json.dumps(answer))  # a fresh copy each time, like a real response
    raise OSError(f"HTTP Error 404: {url}")


def fake_get(url, data=None, hops=5):
    if url in PAGES:
        return PAGES[url]
    raise OSError(f"HTTP Error 404: {url}")


@mock.patch.object(sources, "get_json", fake_get_json)
@mock.patch.object(sources, "get", fake_get)
class Boards(unittest.TestCase):
    KEYS = {"id", "title", "company", "location", "date", "url", "source", "description"}

    def jobs(self, ats, **company):
        found = list(sources.ATS[ats](company))
        for j in found:
            self.assertEqual(set(j), self.KEYS)
            if callable(j["description"]):
                j["description"] = j["description"]()
        return found

    def test_greenhouse(self):
        first = self.jobs("greenhouse", name="Acme", slug="acme")[0]
        self.assertEqual(first["id"], "gh-acme-1")
        self.assertEqual((first["company"], first["location"]), ("Acme", "Tel Aviv"))
        self.assertEqual(first["description"], "Own & automate ops")  # escaped twice in the API

    def test_lever_with_no_location(self):
        (job,) = self.jobs("lever", slug="beta")
        self.assertEqual((job["company"], job["location"]), ("beta", " (Remote)"))
        self.assertEqual(job["date"][:10], RECENT)
        self.assertIn("You will\n- Automate billing", job["description"])

    def test_ashby_skips_unlisted_jobs(self):
        self.assertEqual([j["id"] for j in self.jobs("ashby", name="Gamma", slug="gamma")], ["ab-gamma-g1"])

    def test_workable(self):
        (job,) = self.jobs("workable", slug="delta")
        self.assertEqual(
            (job["company"], job["location"], job["description"]), ("Delta Ltd", "Haifa, Israel (Remote)", "Lead ops")
        )

    def test_smartrecruiters_fetches_the_description_only_when_asked(self):
        (job,) = self.jobs("smartrecruiters", slug="Eps")
        self.assertEqual(job["url"], "https://jobs.smartrecruiters.com/Eps/e1")
        self.assertEqual(job["description"], "The job\nRun it")

    def test_comeet_reads_its_token_from_the_page(self):
        (job,) = self.jobs("comeet", name="Zeta", url="https://www.comeet.com/jobs/zeta/A1.B2C")
        self.assertEqual((job["id"], job["description"]), ("cm-A1.B2C-C1", "Description\nDo it"))

    def test_comeet_with_a_wrong_url_says_so(self):
        with self.assertRaisesRegex(ValueError, "not a Comeet jobs page"):
            self.jobs("comeet", url="https://www.comeet.com/careers")

    def test_remotive(self):
        (job,) = sources.remotive("operations")
        self.assertEqual((job["id"], job["location"]), ("rm-9", "Remote: Worldwide"))

    def test_guess_tries_the_name_as_a_slug(self):
        self.assertEqual(sources.guess("Acme"), ['- {name: "Acme", ats: greenhouse, slug: "acme"}   # 5 open jobs'])
        self.assertIn("not found by name", sources.guess("Nobody Inc")[0])


class Detect(unittest.TestCase):
    CASES = {
        '<script src="https://boards.greenhouse.io/embed/job_board/js?for=acme"></script>': 'ats: greenhouse, slug: "acme"',
        '<a href="https://job-boards.greenhouse.io/acme/jobs/1">': 'ats: greenhouse, slug: "acme"',
        '<a href="https://jobs.lever.co/acme/123">': 'ats: lever, slug: "acme"}',
        '<a href="https://jobs.eu.lever.co/acme">': 'ats: lever, slug: "acme", eu: true}',
        '<iframe src="https://jobs.ashbyhq.com/acme/embed">': 'ats: ashby, slug: "acme"',
        '<a href="https://apply.workable.com/acme/">': 'ats: workable, slug: "acme"',
        '<a href="https://careers.smartrecruiters.com/Acme1">': 'ats: smartrecruiters, slug: "Acme1"',
        '<a href="https://www.comeet.com/jobs/acme/A1.B2C/ops/X">': 'ats: comeet, url: "https://www.comeet.com/jobs/acme/A1.B2C"',
        "<p>Email us your CV</p>": "# no known job board found",
    }

    def test_finds_the_board_a_careers_page_links_to(self):
        for page, expected in self.CASES.items():
            with self.subTest(page), mock.patch.object(sources, "get", lambda url, page=page: page):
                self.assertIn(expected, sources.detect("https://acme.example/careers"))

    def test_a_page_that_wont_open(self):
        with mock.patch.object(sources, "get", fake_get):
            self.assertIn("# couldn't open", sources.detect("https://acme.example/careers"))


class HtmlToText(unittest.TestCase):
    def test_keeps_paragraphs_and_list_items(self):
        html = "<h2>About</h2><p>We&#39;re <b>hiring</b>.</p><ul><li>Own ops</li><li>Automate</li></ul><br/>Thanks"
        self.assertEqual(sources.text(html), "About\nWe're hiring.\n- Own ops\n- Automate\nThanks")


SEARCH_YAML = """
days: 14
linkedin: {queries: []}
title_keywords: [operations, automation]
title_exclude: [intern]
locations: [Tel Aviv, Remote]
companies:
  - {name: Acme, ats: greenhouse, slug: acme}
  - {name: Beta, ats: lever, slug: beta}
  - {name: Nope, ats: teamtailor, slug: nope}
remote:
  queries: [operations, ops]
  allowed_locations: [worldwide]
"""


@mock.patch.object(sources, "get_json", fake_get_json)
@mock.patch.object(sources, "get", fake_get)
class Search(KitTest):
    def search(self, ws, batch):
        out = io.StringIO()
        argv = ["search.py", batch, "--only", "companies,remote", "--workspace", ws]
        with mock.patch.object(sys, "argv", argv), mock.patch("time.sleep"), contextlib.redirect_stdout(out):
            runpy.run_path(os.path.join(KIT, "search.py"), run_name="__main__")
        return out.getvalue(), json.loads(read(os.path.join(ws, "batches", batch, "jobs_all.json")))

    def test_filters_merges_and_marks_new_jobs(self):
        ws = self.workspace(demo=False)
        write(os.path.join(ws, "search.yaml"), SEARCH_YAML)
        out, jobs = self.search(ws, "b1")
        # Acme: not the intern, not Berlin, not 30 days old, not "Retail" (no whole-word keyword)
        self.assertEqual(sorted(jobs), ["gh-acme-1", "lv-beta-b1", "rm-9"])
        self.assertIn("Acme: 1 matching", out)
        self.assertIn("Nope: unknown ats 'teamtailor'", out)
        self.assertEqual(jobs["rm-9"]["q"], ["operations", "ops"])
        self.assertTrue(all(j["new"] for j in jobs.values()))
        jd = read(os.path.join(ws, "batches", "b1", "jd", "gh-acme-1.txt"))
        self.assertTrue(jd.startswith("ID: gh-acme-1\nTITLE: Operations Lead\nCOMPANY: Acme\n"))
        self.assertTrue(jd.endswith("---\nOwn & automate ops"))

        self.search(ws, "b1")  # the same batch again: nothing doubles
        _, again = self.search(ws, "b1")
        self.assertEqual(again["rm-9"]["q"], ["operations", "ops"])

        _, later = self.search(ws, "b2")
        self.assertFalse(any(j["new"] for j in later.values()))


if __name__ == "__main__":
    unittest.main()
