import asyncio
from typing import List, Dict

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KrakenScraper(BaseScraper):
    COMPANY_NAME = "kraken"
    # Ashby board filtered to Engineering dept + Brazil location (Full-time)
    URL = "https://jobs.ashbyhq.com/kraken.com?departmentId=5f67bd79-103b-4ac1-8d79-952b45ea47c9&employmentType=FullTime&locationId=0ae979f7-78d9-4e42-8cf1-831610586017"

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        with self._browser() as browser:
            page = browser.new_page()
            try:
                logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")
                page.goto(self.URL, wait_until="networkidle")
                page.wait_for_timeout(2000)

                # Collect all job links
                job_data = page.evaluate("""() => {
                    const seen = new Set();
                    const jobs = [];
                    for (const a of document.querySelectorAll('a[href*="/kraken.com/"]')) {
                        const href = a.href;
                        // innerText respects CSS layout; first line = job title only
                        const firstLine = (a.innerText || '').split('\\n')[0].trim();
                        if (href && firstLine && !seen.has(href)) {
                            seen.add(href);
                            jobs.push({url: href, title: firstLine});
                        }
                    }
                    return jobs;
                }""") or []

                logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs")

                for job_info in job_data:
                    try:
                        page.goto(job_info["url"], wait_until="domcontentloaded")
                        page.wait_for_timeout(1500)

                        loc_el = page.locator('[class*="location"], [data-testid*="location"]')
                        location = loc_el.first.inner_text().strip() if loc_el.count() > 0 else "Remote"
                        if not location:
                            location = "Remote"

                        # Extract "The opportunity" and "Skills you should HODL" sections
                        requirements = page.evaluate("""() => {
                            const results = [];
                            const seen = new Set();
                            for (const h of document.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
                                const t = h.textContent.trim().toLowerCase();
                                if (!t.includes('the opportunity') && !t.includes('skills you should hodl')) continue;
                                const next = h.nextElementSibling || h.parentElement.nextElementSibling;
                                if (!next) continue;
                                for (const item of next.querySelectorAll('li, p')) {
                                    const text = item.textContent.trim();
                                    if (text.length > 10 && !seen.has(text)) {
                                        seen.add(text);
                                        results.push(text);
                                    }
                                }
                            }
                            return results;
                        }""") or []

                        description = page.evaluate("() => document.body.innerText") or ""

                        job = self.create_job_dict(
                            title=job_info["title"],
                            requirements=requirements[:15],
                            location=location,
                            url=job_info["url"],
                            description=description,
                        )
                        jobs.append(job)
                        logger.info(f"{self.COMPANY_NAME}: Scraped - {job_info['title']} - {len(requirements)} reqs")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping {job_info['url']}: {e}")
                        continue

            finally:
                logger.info(f"{self.COMPANY_NAME}: Done. Total: {len(jobs)}")

        return jobs
