import asyncio
import time
from typing import List, Dict

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AirbnbScraper(BaseScraper):
    COMPANY_NAME = "airbnb"
    # Brazil location filter returns 0 results — scrape all Engineering positions instead.
    # The listing shows Brazil-specific roles (location text in each card).
    BASE_URL = "https://careers.airbnb.com/positions/?_departments=engineering"

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _collect_page_jobs(self, driver) -> list:
        """Return job link data from the currently rendered listing page."""
        return driver.execute_script("""
            return Array.from(document.querySelectorAll('a[href*="/positions/"]'))
                .map(function(a) {
                    return {
                        href: a.href,
                        title: a.textContent.trim(),
                        parentText: a.parentElement ? a.parentElement.textContent.trim() : ''
                    };
                })
                .filter(function(j) {
                    return j.href &&
                        j.href.indexOf('?') === -1 &&
                        j.href.indexOf('#') === -1 &&
                        j.title.length > 2;
                });
        """) or []

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        driver = self._create_driver()
        try:
            logger.info(f"{self.COMPANY_NAME}: Loading {self.BASE_URL}")
            driver.get(self.BASE_URL)
            time.sleep(6)

            seen_hrefs: set = set()
            page_num = 1

            while page_num <= 10:  # safety cap
                # Scroll to trigger lazy-load
                for _ in range(2):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0)")
                time.sleep(1)

                job_data = self._collect_page_jobs(driver)
                new_jobs = [j for j in job_data if j["href"] not in seen_hrefs]
                logger.info(f"{self.COMPANY_NAME}: Page {page_num} — {len(job_data)} links, {len(new_jobs)} new")

                for item in new_jobs:
                    seen_hrefs.add(item["href"])
                    try:
                        driver.get(item["href"])
                        time.sleep(3)

                        # Location from parentText (e.g. "Hybrid • São Paulo, Brazil")
                        location = "Remote"
                        parent_text = item.get("parentText", "")
                        if "•" in parent_text:
                            parts = parent_text.split("•")
                            if len(parts) >= 2:
                                loc = parts[-1].strip()
                                location = loc or "Remote"

                        # Extract from "Your Expertise" section
                        requirements = driver.execute_script("""
                            var results = [];
                            var headings = document.querySelectorAll('h2, h3, h4, strong');
                            var found = null;
                            for (var i = 0; i < headings.length; i++) {
                                if (headings[i].textContent.trim().toLowerCase().indexOf('your expertise') !== -1) {
                                    found = headings[i];
                                    break;
                                }
                            }
                            if (!found) return results;
                            var next = found.nextElementSibling || found.parentElement.nextElementSibling;
                            if (!next) return results;
                            var items = next.querySelectorAll('li, p');
                            for (var j = 0; j < items.length; j++) {
                                var t = items[j].textContent.trim();
                                if (t.length > 10) results.push(t);
                            }
                            return results;
                        """) or []

                        job = self.create_job_dict(
                            title=item["title"],
                            requirements=requirements[:15],
                            location=location,
                            url=item["href"],
                        )
                        jobs.append(job)
                        logger.info(f"{self.COMPANY_NAME}: Scraped - {item['title']} ({location}) - {len(requirements)} reqs")

                        # Go back to the listing page
                        driver.back()
                        time.sleep(3)

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping {item['href']}: {e}")
                        driver.get(self.BASE_URL)
                        time.sleep(4)
                        continue

                # Try to click next page
                try:
                    next_btn = driver.execute_script("""
                        var links = document.querySelectorAll('a.facetwp-page.next');
                        return links.length > 0 ? links[0] : null;
                    """)
                    if not next_btn:
                        logger.info(f"{self.COMPANY_NAME}: No more pages after page {page_num}")
                        break
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(4)
                    page_num += 1
                except Exception as e:
                    logger.info(f"{self.COMPANY_NAME}: Pagination ended at page {page_num}: {e}")
                    break

        finally:
            driver.quit()
            logger.info(f"{self.COMPANY_NAME}: Driver closed. Total: {len(jobs)}")

        return jobs
