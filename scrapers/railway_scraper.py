import asyncio
from typing import List, Dict

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RailwayScraper(BaseScraper):
    COMPANY_NAME = "railway"
    URL = "https://railway.com/careers#open-positions"

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

                # Collect job links
                job_data = page.evaluate("""() => {
                    const seen = new Set();
                    const jobs = [];
                    for (const a of document.querySelectorAll('a[href*="/careers/"]')) {
                        const href = a.href;
                        if (!href || href.replace(/\\/$/, '').endsWith('/careers')) continue;
                        if (seen.has(href)) continue;
                        seen.add(href);
                        let title = a.textContent.trim();
                        let location = 'Remote';
                        if (title.includes('Anywhere')) {
                            location = 'Anywhere';
                            title = title.replace('Anywhere', '').trim();
                        } else if (title.includes('Hybrid')) {
                            location = 'Hybrid';
                            title = title.replace('Hybrid', '').trim();
                        }
                        title = title.replace(/[:\\s-]+$/, '').trim();
                        if (title) jobs.push({url: href, title, location});
                    }
                    return jobs;
                }""") or []

                logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs")

                for job_info in job_data:
                    try:
                        page.goto(job_info["url"], wait_until="domcontentloaded")
                        page.wait_for_timeout(1500)

                        # Extract requirements: all <li> between #about-you and #things-to-know
                        requirements = page.evaluate("""() => {
                            const results = [];
                            const start = document.getElementById('about-you');
                            if (!start) return results;
                            let el = start.nextElementSibling;
                            while (el) {
                                if (el.id === 'things-to-know') break;
                                if (el.tagName === 'LI') {
                                    const t = el.textContent.trim();
                                    if (t.length > 10) results.push(t);
                                }
                                el = el.nextElementSibling;
                            }
                            return results;
                        }""") or []

                        description = page.evaluate("() => document.body.innerText") or ""

                        job = self.create_job_dict(
                            title=job_info["title"],
                            requirements=requirements[:15],
                            location=job_info["location"],
                            url=job_info["url"],
                            description=description,
                        )
                        jobs.append(job)
                        logger.info(f"{self.COMPANY_NAME}: Scraped - {job_info['title']} ({job_info['location']}) - {len(requirements)} reqs")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping {job_info['url']}: {e}")
                        continue

            finally:
                logger.info(f"{self.COMPANY_NAME}: Done. Total: {len(jobs)}")

        return jobs
