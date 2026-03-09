import asyncio
import time
from typing import List, Dict

from selenium.webdriver.common.by import By

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AirbnbScraper(BaseScraper):
    COMPANY_NAME = "airbnb"
    BASE_URL = "https://careers.airbnb.com/positions/?_departments=engineering&_where_you_work=brazil-63869%2Csao-paulo-brazil-176"

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        driver = self._create_driver()
        try:
            for page_num in [1, 2]:
                url = f"{self.BASE_URL}&page={page_num}" if page_num > 1 else self.BASE_URL
                logger.info(f"{self.COMPANY_NAME}: Scraping page {page_num} - {url}")

                driver.get(url)
                time.sleep(3)
                logger.info(f"{self.COMPANY_NAME}: Page {page_num} loaded")

                # Collect job links and basic info from listing page
                links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/positions/"]')
                logger.info(f"{self.COMPANY_NAME}: Found {len(links)} job links on page {page_num}")

                job_data = []
                for link in links:
                    try:
                        href = link.get_attribute("href") or ""
                        if not href or "/positions/?" in href:
                            continue

                        title = link.text.strip()
                        if not title or href in [j["url"] for j in job_data]:
                            continue

                        # Get location from parent element text
                        parent_text = driver.execute_script(
                            "return arguments[0].parentElement.textContent", link
                        ) or ""
                        location = "Remote"
                        if "Hybrid" in parent_text and "•" in parent_text:
                            parts = parent_text.split("•")
                            if len(parts) >= 2:
                                loc = parts[1].strip()
                                if title in loc:
                                    loc = loc.replace(title, "").strip()
                                location = loc or "Remote"

                        job_data.append({"url": href, "title": title, "location": location})
                    except Exception as e:
                        logger.debug(f"{self.COMPANY_NAME}: Error reading link: {e}")
                        continue

                logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs on page {page_num}")

                # Visit each detail page
                for job_info in job_data:
                    try:
                        driver.get(job_info["url"])
                        time.sleep(2)

                        # Extract from "Your Expertise" section
                        requirements = driver.execute_script("""
                            const results = [];
                            const headings = document.querySelectorAll('h2, h3, h4, strong');
                            let expertiseHeading = null;
                            for (const h of headings) {
                                if (h.textContent.trim().toLowerCase().includes('your expertise')) {
                                    expertiseHeading = h;
                                    break;
                                }
                            }
                            if (!expertiseHeading) return results;
                            const next = expertiseHeading.nextElementSibling
                                || expertiseHeading.parentElement.nextElementSibling;
                            if (!next) return results;
                            const items = next.querySelectorAll('li, p');
                            for (const item of items) {
                                const t = item.textContent.trim();
                                if (t.length > 10) results.push(t);
                            }
                            return results;
                        """)

                        job = self.create_job_dict(
                            title=job_info["title"],
                            requirements=(requirements or [])[:15],
                            location=job_info["location"],
                            url=job_info["url"],
                        )
                        jobs.append(job)
                        logger.info(f"{self.COMPANY_NAME}: Scraped job - {job_info['title']} ({job_info['location']}) - {len(requirements or [])} requirements")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping {job_info['url']}: {e}")
                        continue

                logger.info(f"{self.COMPANY_NAME}: Found {len(job_data)} jobs on page {page_num}")

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed")

        logger.info(f"{self.COMPANY_NAME}: Total jobs scraped: {len(jobs)}")
        return jobs
