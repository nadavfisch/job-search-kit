"""LinkedIn's real public pages, read the way kit/search.py and kit/fetch_jd.py read them.

The other tests run offline, so they can't notice when LinkedIn changes these pages and the search quietly stops
finding jobs. This one can. It runs only when JOBKIT_LIVE=1 is set: once a week in CI (.github/workflows/live.yml),
or by hand:
  JOBKIT_LIVE=1 python3 -m unittest discover -s tests -p test_live.py -v
Three search pages and three job pages, a second and a half apart. When LinkedIn refuses to answer (rate-limited,
blocked), the test is skipped: that says nothing about whether the kit can still read the pages.
"""

import os
import time
import unittest

import helpers  # noqa: F401  (puts kit/ on the import path)

import sources


@unittest.skipUnless(os.environ.get("JOBKIT_LIVE"), "reads LinkedIn's real pages: set JOBKIT_LIVE=1")
class LinkedIn(unittest.TestCase):
    def fetch(self, url):
        time.sleep(1.5)
        try:
            page = sources.get(url)
        except Exception as e:
            self.skipTest(f"LinkedIn didn't answer ({e}), so the pages weren't checked")
        if sources.linkedin_empty(page):
            self.skipTest("LinkedIn sent an empty page (rate-limited?), so the pages weren't checked")
        return page

    def search(self, start=0):
        page = self.fetch(sources.linkedin_search_url("operations manager", "United States", days=7, start=start))
        cards = sources.linkedin_cards(page)
        self.assertTrue(cards, f"no jobs in a search page of {len(page)} characters. {sources.LINKEDIN_CHANGED}")
        for field in ("title", "company", "location", "date"):
            have = sum(bool(j[field]) for j in cards)
            self.assertGreater(have, len(cards) / 2, f"{have} of {len(cards)} jobs have a {field}")
        return cards

    def test_search_pages(self):
        first = self.search()
        second = self.search(start=len(first))  # search.py pages by the number of jobs each page had
        self.assertFalse({j["id"] for j in first} & {j["id"] for j in second}, "the second page repeats the first")

    def test_job_pages(self):
        posts = [sources.linkedin_posting(self.fetch(sources.linkedin_posting_url(j["id"]))) for j in self.search()[:3]]
        for post in posts:
            self.assertGreater(len(post["description"]), 100, f"no description. {sources.LINKEDIN_CHANGED}")
        self.assertTrue(any(p["criteria"] for p in posts), "no criteria (seniority, employment type) on any job page")
        self.assertTrue(any(p["applicants"] for p in posts), "no applicant count on any job page")


if __name__ == "__main__":
    unittest.main()
