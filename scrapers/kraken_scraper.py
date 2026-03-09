import asyncio
import time
from typing import List, Dict

from selenium.webdriver.common.by import By

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KrakenScraper(BaseScraper):
    COMPANY_NAME = "kraken"
    URL = "https://jobs.ashbyhq.com/kraken.com?departmentId=5f67bd79-103b-4ac1-8d79-952b45ea47c9&employmentType=FullTime&locationId=0ae979f7-78d9-4e42-8cf1-831610586017"

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        driver = self._create_driver()
        try:
            logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")
            driver.get(self.URL)
            time.sleep(3)
            logger.info(f"{self.COMPANY_NAME}: Page loaded")

            # Collect all job links
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/kraken.com/"]')
            logger.info(f"{self.COMPANY_NAME}: Found {len(links)} job links")

            job_data = []
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    if not href:
                        continue
                    title = link.text.strip()
                    if not title or href in [j["url"] for j in job_data]:
                        continue
                    job_data.append({"url": href, "title": title})
                except Exception as e:
                    logger.debug(f"{self.COMPANY_NAME}: Error reading link: {e}")
                    continue

            logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs")

            for job_info in job_data:
                try:
                    driver.get(job_info["url"])
                    time.sleep(2)

                    location = self.safe_get_text(
                        driver, '[class*="location"], [data-testid*="location"]', "Remote"
                    )

                    # Extract from "The opportunity" and "Skills you should HODL" sections
                    requirements = driver.execute_script("""
                        const results = [];
                        const headings = document.querySelectorAll('h1,h2,h3,h4,h5,h6');
                        for (const h of headings) {
                            const t = h.textContent.trim().toLowerCase();
                            if (!t.includes('the opportunity') && !t.includes('skills you should hodl')) continue;
                            const next = h.nextElementSibling || h.parentElement.nextElementSibling;
                            if (!next) continue;
                            const items = next.querySelectorAll('li, p');
                            for (const item of items) {
                                const text = item.textContent.trim();
                                if (text.length > 10) results.push(text);
                            }
                        }
                        return results;
                    """)

                    job = self.create_job_dict(
                        title=job_info["title"],
                        requirements=(requirements or [])[:15],
                        location=location,
                        url=job_info["url"],
                    )
                    jobs.append(job)
                    logger.info(f"{self.COMPANY_NAME}: Scraped job - {job_info['title']} ({location}) - {len(requirements or [])} requirements")

                except Exception as e:
                    logger.warning(f"{self.COMPANY_NAME}: Error scraping {job_info['url']}: {e}")
                    continue

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed")

        return jobs
