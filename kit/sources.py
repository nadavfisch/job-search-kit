"""Job sources besides LinkedIn: company career pages (public job-board APIs) and remote job boards.

  python3 kit/sources.py guess <company name>          # try the name on each job board -> a line for search.yaml
  python3 kit/sources.py detect <careers page url>    # find the job board linked from a careers page

Every fetcher yields the same shape: {id, title, company, location, date, url, source, description}.
`description` may be a function, so detail pages are fetched only for jobs that pass the filters.
"""

import datetime
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def get(url, data=None, hops=5):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    try:
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:  # urllib follows no 308 before Python 3.11, and no 307 after a POST
        if e.code in (307, 308) and hops and e.headers.get("Location"):
            return get(urllib.parse.urljoin(url, e.headers["Location"]), data, hops - 1)
        raise


def get_json(url):
    return json.loads(get(url))


def text(h):
    """HTML -> plain text with line breaks."""
    h = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", h or "", flags=re.I)
    h = re.sub(r"<li[^>]*>", "\n- ", h, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", h))
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def greenhouse(c):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{c['slug']}/jobs?content=true")
    for j in d.get("jobs", []):
        yield dict(
            id=f"gh-{c['slug']}-{j['id']}",
            title=j["title"],
            company=c.get("name") or j.get("company_name", ""),
            location=(j.get("location") or {}).get("name", ""),
            date=j.get("first_published") or j.get("updated_at", ""),
            url=j["absolute_url"],
            source="greenhouse",
            description=text(html.unescape(j.get("content", ""))),
        )


def lever(c):
    host = "api.eu.lever.co" if c.get("eu") else "api.lever.co"
    for j in get_json(f"https://{host}/v0/postings/{c['slug']}?mode=json"):
        lists = "\n".join(f"{x.get('text', '')}\n{text(x.get('content', ''))}" for x in j.get("lists") or [])
        created = (
            datetime.datetime.fromtimestamp(j["createdAt"] / 1000, datetime.timezone.utc).isoformat()
            if j.get("createdAt")
            else ""
        )
        yield dict(
            id=f"lv-{c['slug']}-{j['id']}",
            title=j["text"],
            company=c.get("name", c["slug"]),
            location=((j.get("categories") or {}).get("location") or "")
            + (" (Remote)" if j.get("workplaceType") == "remote" else ""),
            date=created,
            url=j["hostedUrl"],
            source="lever",
            description="\n".join([j.get("descriptionPlain", ""), lists, j.get("additionalPlain", "")]).strip(),
        )


def ashby(c):
    for j in get_json(f"https://api.ashbyhq.com/posting-api/job-board/{c['slug']}").get("jobs", []):
        if j.get("isListed") is False:
            continue
        yield dict(
            id=f"ab-{c['slug']}-{j['id']}",
            title=j["title"],
            company=c.get("name", c["slug"]),
            location=(j.get("location") or "") + (" (Remote)" if j.get("isRemote") else ""),
            date=j.get("publishedAt", ""),
            url=j["jobUrl"],
            source="ashby",
            description=j.get("descriptionPlain") or text(j.get("descriptionHtml", "")),
        )


def workable(c):
    d = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{c['slug']}?details=true")
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in (j.get("city"), j.get("country")) if x) + (
            " (Remote)" if j.get("telecommuting") else ""
        )
        yield dict(
            id=f"wk-{c['slug']}-{j['shortcode']}",
            title=j["title"],
            company=c.get("name") or d.get("name", ""),
            location=loc,
            date=j.get("published_on") or j.get("created_at", ""),
            url=j["url"],
            source="workable",
            description=text(j.get("description", "")),
        )


def smartrecruiters(c):
    base = f"https://api.smartrecruiters.com/v1/companies/{c['slug']}/postings"
    for offset in range(0, 1000, 100):
        d = get_json(f"{base}?limit=100&offset={offset}")
        for j in d.get("content", []):
            loc = j.get("location") or {}

            def detail(jid=j["id"]):  # fetched later, only if the job passes the filters
                return "\n".join(
                    f"{s.get('title', '')}\n{text(s.get('text', ''))}"
                    for s in get_json(f"{base}/{jid}")["jobAd"]["sections"].values()
                    if s.get("text")
                )

            yield dict(
                id=f"sr-{c['slug']}-{j['id']}",
                title=j["name"],
                company=c.get("name") or (j.get("company") or {}).get("name", ""),
                location=loc.get("fullLocation", "") + (" (Remote)" if loc.get("remote") else ""),
                date=j.get("releasedDate", ""),
                url=f"https://jobs.smartrecruiters.com/{c['slug']}/{j['id']}",
                source="smartrecruiters",
                description=detail,
            )
        if offset + 100 >= d.get("totalFound", 0):
            break


def comeet(c):
    """c['url'] = the company's Comeet page, e.g. https://www.comeet.com/jobs/<slug>/<uid>. Its public token is in the page."""
    uid = re.search(r"/jobs/[^/]+/([0-9A-F]{2}\.[0-9A-F]{3})", c.get("url", ""), re.I)
    if not uid:
        raise ValueError(f"not a Comeet jobs page (https://www.comeet.com/jobs/<company>/<XX.XXX>): {c.get('url')!r}")
    token = re.search(r'"token"\s*:\s*"([0-9A-F]{20,})"', get(c["url"]), re.I)
    if not token:
        raise ValueError(f"no Comeet token found in {c['url']}")
    uid, token = uid.group(1), token.group(1)
    for j in get_json(f"https://www.comeet.co/careers-api/2.0/company/{uid}/positions?token={token}&details=true"):
        loc = j.get("location") or {}
        yield dict(
            id=f"cm-{uid}-{j['uid']}",
            title=j["name"],
            company=c.get("name") or j.get("company_name", ""),
            location=(loc.get("name") or "") + (" (Remote)" if loc.get("is_remote") else ""),
            date=j.get("time_updated", ""),
            url=j.get("url_active_page") or j.get("url_comeet_hosted_page", ""),
            source="comeet",
            description="\n".join(f"{x.get('name', '')}\n{text(x.get('value', ''))}" for x in j.get("details") or []),
        )


def remotive(query):
    for j in get_json(
        "https://remotive.com/api/remote-jobs?" + urllib.parse.urlencode({"search": query, "limit": 50})
    ).get("jobs", []):
        yield dict(
            id=f"rm-{j['id']}",
            title=j["title"],
            company=j.get("company_name", ""),
            location="Remote: " + (j.get("candidate_required_location") or "anywhere"),
            date=j.get("publication_date", ""),
            url=j["url"],
            source="remotive",
            description=text(j.get("description", "")),
        )


ATS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workable": workable,
    "smartrecruiters": smartrecruiters,
    "comeet": comeet,
}

DETECT = [
    (
        "greenhouse",
        r"(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board(?:/js)?\?for=)?([A-Za-z0-9_-]+)",
    ),
    ("greenhouse", r"greenhouse\.io/embed/job_board(?:/js)?\?for=([A-Za-z0-9_-]+)"),
    ("lever", r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_.-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)"),
    ("workable", r"apply\.workable\.com/([A-Za-z0-9_-]+)"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)"),
    ("comeet", r"(https://www\.comeet\.com/jobs/[A-Za-z0-9_-]+/[0-9A-F]{2}\.[0-9A-F]{3})"),
]
SKIP_SLUGS = {"embed", "api", "j", "jobs", "js", "v1", "v0", "widget", "assets", "static"}


def detect(url):
    """Look for a known job board in the careers page (and the URL itself)."""
    try:
        page = url + "\n" + get(url)
    except Exception as e:
        return f"# couldn't open {url}: {e}"
    for ats, pat in DETECT:
        for m in re.finditer(pat, page, re.I):
            slug = m.group(1)
            if slug.lower() in SKIP_SLUGS:
                continue
            if ats == "comeet":
                return f'- {{name: "<company>", ats: comeet, url: "{slug}"}}'
            return (
                f'- {{name: "<company>", ats: {ats}, slug: "{slug}"{", eu: true" if "eu.lever" in m.group(0) else ""}}}'
            )
    return "# no known job board found: the agent checks this company in the browser instead"


def guess(name):
    """Try the company name as a slug on each job board's API. Returns the lines that found open jobs."""
    base = re.sub(r"[^a-z0-9 -]", "", name.lower()).strip()
    slugs = list(dict.fromkeys([base.replace(" ", ""), base.replace(" ", "-"), base.split(" ")[0]]))
    found = []
    for ats in ("greenhouse", "lever", "ashby", "workable"):
        for slug in slugs:
            try:
                n = sum(1 for _ in ATS[ats]({"slug": slug, "name": name}))
            except Exception:
                continue
            if n:
                found.append(
                    f'- {{name: {json.dumps(name, ensure_ascii=False)}, ats: {ats}, slug: "{slug}"}}   # {n} open jobs'
                )
                break
    return found or [f"# {name}: not found by name. Find the careers page and run: python3 kit/sources.py detect <url>"]


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "detect":
        print(detect(sys.argv[2]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "guess":
        print("\n".join(guess(" ".join(sys.argv[2:]))))
    else:
        sys.exit(__doc__)
