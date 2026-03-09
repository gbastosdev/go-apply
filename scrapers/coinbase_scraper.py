import asyncio
import time
from typing import List, Dict

from selenium.webdriver.common.by import By

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CoinbaseScraper(BaseScraper):
    COMPANY_NAME = "coinbase"
    URLS = [
        "https://www.coinbase.com/pt-br/careers/positions?department=Engineering&location=remote",
        "https://www.coinbase.com/pt-br/careers/positions?department=Engineering+-+Backend&location=remote",
        "https://www.coinbase.com/pt-br/careers/positions?department=Engineering+-+Frontend&location=remote",
    ]

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        all_jobs: Dict[str, dict] = {}
        driver = self._create_driver()
        try:
            for url in self.URLS:
                logger.info(f"{self.COMPANY_NAME}: Scraping {url}")
                driver.get(url)
                time.sleep(4)
                logger.info(f"{self.COMPANY_NAME}: Page loaded - {url}")

                # Collect job links from listing page
                job_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/careers/position"]')
                if not job_links:
                    job_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/careers/"]')

                logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links on page")

                hrefs = []
                for link in job_links:
                    href = link.get_attribute("href") or ""
                    if href and href not in hrefs:
                        hrefs.append(href)

                for job_url in hrefs[:40]:
                    if job_url in all_jobs:
                        continue
                    try:
                        driver.get(job_url)
                        time.sleep(2)

                        title = self.safe_get_text(driver, "h1, h2", "Unknown Position")
                        location = self.safe_get_text(driver, '[class*="location"]', "Remote")

                        # Extract requirements from common section headings
                        requirements = driver.execute_script("""
                            const results = [];
                            const keywords = ["what you'll bring", "requirements",
                                              "qualifications", "what we look for",
                                              "minimum qualifications"];
                            const headings = document.querySelectorAll('h2, h3');
                            for (const h of headings) {
                                const t = h.textContent.trim().toLowerCase();
                                if (!keywords.some(k => t.includes(k))) continue;
                                const parent = h.parentElement;
                                const items = parent.querySelectorAll('li');
                                for (const item of items) {
                                    const text = item.textContent.trim();
                                    if (text.length > 10) results.push(text);
                                }
                            }
                            if (results.length === 0) {
                                const items = document.querySelectorAll('ul li');
                                for (const item of items) {
                                    const text = item.textContent.trim();
                                    if (text.length > 10) results.push(text);
                                    if (results.length >= 15) break;
                                }
                            }
                            return results;
                        """)

                        job = self.create_job_dict(
                            title=title,
                            requirements=(requirements or [])[:15],
                            location=location,
                            url=job_url,
                        )
                        all_jobs[job_url] = job
                        logger.debug(f"{self.COMPANY_NAME}: Scraped job - {title}")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping {job_url}: {e}")
                        continue

                logger.info(f"{self.COMPANY_NAME}: Found {len(hrefs)} jobs from this department")

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed")

        result = list(all_jobs.values())
        logger.info(f"{self.COMPANY_NAME}: Total unique jobs: {len(result)}")
        return result
