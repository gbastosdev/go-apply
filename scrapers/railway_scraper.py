import asyncio
import time
from typing import List, Dict

from selenium.webdriver.common.by import By

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
        driver = self._create_driver()
        try:
            logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")
            driver.get(self.URL)
            time.sleep(3)

            # Collect all job links
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/careers/"]')
            logger.info(f"{self.COMPANY_NAME}: Found {len(links)} job links")

            job_data = []
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    if not href or href.rstrip("/").endswith("/careers"):
                        continue

                    title = link.text.strip()
                    if not title or href in [j["url"] for j in job_data]:
                        continue

                    location = "Remote"
                    if "Anywhere" in title:
                        location = "Anywhere"
                        title = title.replace("Anywhere", "").strip()
                    elif "Hybrid" in title:
                        location = "Hybrid"
                        title = title.replace("Hybrid", "").strip()
                    title = title.rstrip(": -")

                    job_data.append({"url": href, "title": title, "location": location})
                except Exception as e:
                    logger.debug(f"{self.COMPANY_NAME}: Error reading link: {e}")
                    continue

            logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs")

            for job_info in job_data:
                try:
                    driver.get(job_info["url"])
                    time.sleep(2)

                    # Extract requirements: all <li> between #about-you and #things-to-know
                    requirements = driver.execute_script("""
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
                    """)

                    # Use full page text for tech_stack (requirements section alone
                    # rarely names specific technologies explicitly)
                    description = driver.execute_script(
                        "return document.body.innerText"
                    ) or ""

                    job = self.create_job_dict(
                        title=job_info["title"],
                        requirements=(requirements or [])[:15],
                        location=job_info["location"],
                        url=job_info["url"],
                        description=description,
                    )
                    jobs.append(job)
                    logger.info(f"{self.COMPANY_NAME}: Scraped job - {job_info['title']} ({job_info['location']}) - {len(requirements or [])} requirements")

                except Exception as e:
                    logger.warning(f"{self.COMPANY_NAME}: Error scraping {job_info['url']}: {e}")
                    continue

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed")

        return jobs
