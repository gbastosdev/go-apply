import asyncio
from typing import List, Dict

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AirbnbScraper(BaseScraper):
    COMPANY_NAME = "airbnb"
    # Brazil location filter returns 0 — use engineering-only URL.
    # Brazil-specific roles appear in location text (e.g. "Brazil", "São Paulo").
    BASE_URL = "https://careers.airbnb.com/positions/?_departments=engineering"

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        with self._browser() as browser:
            page = browser.new_page()
            try:
                # Phase 1: collect ALL job links across all listing pages
                all_job_data = self._collect_all_job_links(page)
                logger.info(f"{self.COMPANY_NAME}: Total unique jobs found: {len(all_job_data)}")

                # Phase 2: visit each detail page
                for item in all_job_data:
                    try:
                        page.goto(item["url"], wait_until="domcontentloaded")
                        page.wait_for_function("() => document.body && document.body.offsetHeight > 0")
                        page.wait_for_timeout(2000)

                        # Location from detail page (listing card text is multiline noise)
                        location = page.evaluate("""() => {
                            const sel = [
                                '.job-location', '[data-qa="location"]', '.location'
                            ];
                            for (const s of sel) {
                                const el = document.querySelector(s);
                                if (el) {
                                    const t = el.innerText.trim();
                                    if (t && !t.includes('\\n')) return t;
                                }
                            }
                            // Fallback: element after h1 contains "Work Model\\nTitle\\nCity" — last line is city
                            const h1 = document.querySelector('h1');
                            if (h1) {
                                let el = h1.nextElementSibling;
                                for (let i = 0; i < 5; i++) {
                                    if (!el) break;
                                    const lines = el.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                                    if (lines.length >= 2) {
                                        const last = lines[lines.length - 1];
                                        if (last.length < 80) return last;
                                    } else if (lines.length === 1 && lines[0].length < 80) {
                                        return lines[0];
                                    }
                                    el = el.nextElementSibling;
                                }
                            }
                            return 'Remote';
                        }""") or "Remote"

                        # "Your Expertise" section — walk up to 5 ancestor levels
                        # to find sibling LI container (Airbnb uses <p><strong> heading)
                        requirements = page.evaluate("""() => {
                            const results = [];
                            const headings = document.querySelectorAll('h1,h2,h3,h4,h5,h6,strong,b,p');
                            let found = null;
                            for (const h of headings) {
                                if (h.textContent.trim().toLowerCase().includes('your expertise')) {
                                    found = h;
                                    break;
                                }
                            }
                            if (!found) return results;
                            let el = found;
                            for (let depth = 0; depth < 5; depth++) {
                                let sib = el.nextElementSibling;
                                while (sib) {
                                    const lis = sib.querySelectorAll('li');
                                    if (lis.length > 0) {
                                        for (const li of lis) {
                                            const t = li.textContent.trim();
                                            if (t.length > 10) results.push(t);
                                        }
                                        return results;
                                    }
                                    if (sib.tagName === 'LI') {
                                        const t = sib.textContent.trim();
                                        if (t.length > 10) results.push(t);
                                    }
                                    sib = sib.nextElementSibling;
                                }
                                if (!el.parentElement) break;
                                el = el.parentElement;
                            }
                            return results;
                        }""") or []

                        description = page.evaluate("() => document.body.innerText") or ""

                        job = self.create_job_dict(
                            title=item["title"],
                            requirements=requirements[:15],
                            location=location,
                            url=item["url"],
                            description=description,
                        )
                        jobs.append(job)
                        logger.info(f"{self.COMPANY_NAME}: Scraped - {item['title']} ({item['location']}) - {len(requirements)} reqs")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping {item['url']}: {e}")
                        continue

            finally:
                logger.info(f"{self.COMPANY_NAME}: Done. Total: {len(jobs)}")

        return jobs

    def _collect_all_job_links(self, page) -> List[Dict]:
        """Navigate all listing pages and return deduplicated job link data."""
        logger.info(f"{self.COMPANY_NAME}: Loading {self.BASE_URL}")
        page.goto(self.BASE_URL, wait_until="load")
        page.wait_for_function("() => document.body && document.body.offsetHeight > 0")
        page.wait_for_timeout(3000)

        all_jobs: Dict[str, Dict] = {}
        page_num = 1

        while page_num <= 15:  # safety cap
            for _ in range(2):
                page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(800)

            job_data = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href*="/positions/"]'))
                    .map(a => {
                        const parent = a.closest('li') || a.parentElement;
                        const parentText = parent ? parent.innerText : '';
                        let location = 'Remote';
                        if (parentText.includes('\\u2022')) {
                            const parts = parentText.split('\\u2022');
                            location = parts[parts.length - 1].trim() || 'Remote';
                        }
                        return {url: a.href, title: a.textContent.trim(), location};
                    })
                    .filter(j => j.url && !j.url.includes('?') && !j.url.includes('#') && j.title.length > 2);
            }""") or []

            new_count = 0
            for j in job_data:
                if j["url"] not in all_jobs:
                    all_jobs[j["url"]] = j
                    new_count += 1

            logger.info(f"{self.COMPANY_NAME}: Page {page_num} — {len(job_data)} links, {new_count} new (total: {len(all_jobs)})")

            if not job_data:
                logger.info(f"{self.COMPANY_NAME}: No jobs on page {page_num}, stopping")
                break

            # FacetWP "next" button
            next_btn = page.locator("a.facetwp-page.next")
            if next_btn.count() == 0:
                logger.info(f"{self.COMPANY_NAME}: No more pages after page {page_num}")
                break

            next_btn.first.click()
            page.wait_for_timeout(3000)
            page_num += 1

        return list(all_jobs.values())
