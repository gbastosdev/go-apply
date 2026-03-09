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
    ROLES_XPATH = '//*[@id="roles"]/div[1]/div/div[1]/div/div[2]/div/div/div/div/div[1]'

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        driver = self._create_driver()
        try:
            logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")
            driver.get(self.URL)
            time.sleep(4)
            logger.info(f"{self.COMPANY_NAME}: Page loaded")

            # Find the container via XPath
            try:
                container = driver.find_element(By.XPATH, self.ROLES_XPATH)
            except Exception:
                logger.warning(f"{self.COMPANY_NAME}: Container not found at XPath")
                return jobs

            if "build products" not in (container.text or "").lower():
                logger.warning(f"{self.COMPANY_NAME}: Container doesn't contain 'build products'")
                return jobs

            logger.info(f"{self.COMPANY_NAME}: Found 'build products' section")

            # Find job links inside container
            job_links = container.find_elements(By.CSS_SELECTOR, 'a[href*="/careers/"]')
            logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job elements")

            # Collect hrefs and titles before navigating away
            job_data = []
            for link in job_links:
                try:
                    href = link.get_attribute("href") or ""
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = f"https://posthog.com{href}"
                    title = link.text.strip() or "Unknown Position"
                    if href not in [j["url"] for j in job_data]:
                        job_data.append({"url": href, "title": title})
                except Exception:
                    continue

            for job_info in job_data:
                try:
                    driver.get(job_info["url"])
                    time.sleep(2)

                    # Extract requirements from ul li elements
                    requirements = []
                    try:
                        items = driver.find_elements(By.CSS_SELECTOR, "ul li")
                        for item in items[:15]:
                            text = item.text.strip()
                            if text and len(text) > 10:
                                requirements.append(text)
                    except Exception:
                        pass

                    job = self.create_job_dict(
                        title=job_info["title"],
                        requirements=requirements[:15],
                        location="Remote",
                        url=job_info["url"],
                    )
                    jobs.append(job)
                    logger.info(f"{self.COMPANY_NAME}: Scraped job - {job_info['title']} - {len(requirements)} requirements")

                except Exception as e:
                    logger.warning(f"{self.COMPANY_NAME}: Error scraping {job_info['url']}: {e}")
                    continue

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed")

        return jobs
