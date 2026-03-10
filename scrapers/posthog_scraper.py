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
    # XPath to the main roles <ul> — confirmed by user
    ROLES_UL_XPATH = '//*[@id="roles"]/div[1]/div/div[1]/div/div[2]/div/div/div/div/div[1]/ul'

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        driver = self._create_driver()
        try:
            logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")
            driver.get(self.URL)
            time.sleep(5)

            # Scroll to ensure all roles load (Next.js lazy rendering)
            for _ in range(4):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(1)

            # Collect all "Read more" hrefs from the roles ul via XPath
            job_links = self._collect_job_links(driver)
            logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links")

            for href in job_links:
                try:
                    driver.get(href)
                    time.sleep(2)

                    # Title from h1
                    try:
                        title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                    except Exception:
                        title = ""

                    if not title:
                        logger.info(f"{self.COMPANY_NAME}: No h1 found at {href}, skipping")
                        continue

                    # Requirements from ul li on the detail page
                    requirements = driver.execute_script("""
                        var results = [];
                        var items = document.querySelectorAll('ul li');
                        for (var i = 0; i < items.length; i++) {
                            var t = items[i].textContent.trim();
                            if (t.length > 10) results.push(t);
                            if (results.length >= 20) break;
                        }
                        return results;
                    """) or []

                    # Full page text for tech_stack extraction
                    description = driver.execute_script(
                        "return document.body.innerText"
                    ) or ""

                    job = self.create_job_dict(
                        title=title,
                        requirements=requirements[:15],
                        location="Remote",
                        url=href,
                        description=description,
                    )
                    jobs.append(job)
                    logger.info(f"{self.COMPANY_NAME}: Scraped - {title} - {len(requirements)} reqs")

                except Exception as e:
                    logger.warning(f"{self.COMPANY_NAME}: Error scraping {href}: {e}")
                    continue

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed. Total: {len(jobs)}")

        return jobs

    def _collect_job_links(self, driver) -> List[str]:
        """Find all 'Read more' links inside the roles ul. Falls back to page-wide scan."""
        links = []
        try:
            ul = driver.find_element(By.XPATH, self.ROLES_UL_XPATH)
            anchors = ul.find_elements(By.TAG_NAME, "a")
            for a in anchors:
                href = a.get_attribute("href") or ""
                if href and href not in links:
                    links.append(href)
            logger.info(f"{self.COMPANY_NAME}: XPath found {len(links)} links in roles ul")
        except Exception as e:
            logger.warning(f"{self.COMPANY_NAME}: XPath strategy failed ({e}), falling back to page scan")

        if not links:
            # Fallback: any /careers/<slug> link on the page
            links = driver.execute_script("""
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(function(a) { return a.href; })
                    .filter(function(h) {
                        try {
                            var url = new URL(h);
                            return url.hostname.includes('posthog.com') &&
                                   /\\/careers\\/[a-z0-9-]+/.test(url.pathname);
                        } catch(e) { return false; }
                    })
                    .filter(function(h, i, arr) { return arr.indexOf(h) === i; });
            """) or []
            logger.info(f"{self.COMPANY_NAME}: Fallback found {len(links)} links")

        return links
