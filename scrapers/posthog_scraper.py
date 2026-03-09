import asyncio
import time
from typing import List, Dict

from selenium.webdriver.common.by import By

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PostHogScraper(BaseScraper):
    COMPANY_NAME = "posthog"
    URL = "https://posthog.com/careers"

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    _BAD_TITLES = {"read more", "apply", "apply now", "learn more", "view job", "see more", "more", ""}

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        driver = self._create_driver()
        try:
            logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")
            driver.get(self.URL)
            time.sleep(5)

            # Multi-pass scroll to trigger lazy loading
            for _ in range(4):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(1)

            # Find all job links on the page — PostHog job detail pages are
            # under /careers/<slug> (longer than just "/careers" or "/careers#...")
            job_data = driver.execute_script("""
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({href: a.href, title: a.textContent.trim()}))
                    .filter(j => {
                        if (!j.href) return false;
                        try {
                            const url = new URL(j.href);
                            return url.hostname.includes('posthog.com') &&
                                   /\\/careers\\/[a-z0-9-]+/.test(url.pathname);
                        } catch { return false; }
                    });
            """) or []

            # Deduplicate by href
            seen = set()
            unique_jobs = []
            for item in job_data:
                if item["href"] not in seen:
                    seen.add(item["href"])
                    unique_jobs.append(item)

            logger.info(f"{self.COMPANY_NAME}: Found {len(unique_jobs)} job links")

            for item in unique_jobs:
                try:
                    driver.get(item["href"])
                    time.sleep(2)

                    # Always prefer h1 from the detail page for reliable title
                    try:
                        title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                    except Exception:
                        title = item["title"]

                    if not title or title.lower() in self._BAD_TITLES:
                        logger.info(f"{self.COMPANY_NAME}: Skipping bad title '{title}' at {item['href']}")
                        continue

                    # Extract requirements from ul li
                    requirements = driver.execute_script("""
                        const results = [];
                        for (const li of document.querySelectorAll('ul li')) {
                            const t = li.textContent.trim();
                            if (t.length > 10) results.push(t);
                            if (results.length >= 20) break;
                        }
                        return results;
                    """) or []

                    job = self.create_job_dict(
                        title=title,
                        requirements=requirements[:15],
                        location="Remote",
                        url=item["href"],
                    )
                    jobs.append(job)
                    logger.info(f"{self.COMPANY_NAME}: Scraped - {title} - {len(requirements)} reqs")

                except Exception as e:
                    logger.warning(f"{self.COMPANY_NAME}: Error scraping {item['href']}: {e}")
                    continue

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed. Total: {len(jobs)}")

        return jobs
