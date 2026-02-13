from typing import List, Dict
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AirbnbScraper(BaseScraper):
    """Scraper for Airbnb careers page (Engineering department)"""

    COMPANY_NAME = "airbnb"
    URL = "https://careers.airbnb.com/positions/?_departments=engineering"

    async def scrape(self) -> List[Dict]:
        """Scrape job listings from Airbnb engineering careers page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")

                await page.goto(self.URL, timeout=self.TIMEOUT, wait_until="networkidle")
                logger.info(f"{self.COMPANY_NAME}: Page loaded successfully")

                # Wait for job listings to load (Airbnb uses a custom career portal)
                try:
                    await page.wait_for_selector(
                        'div[class*="position"], div[class*="job"], a[href*="/positions/"]',
                        timeout=20000
                    )
                except Exception:
                    logger.warning(f"{self.COMPANY_NAME}: Standard selectors not found")

                # Find all position cards/links
                job_links = await page.query_selector_all('a[href*="/positions/"]')

                if not job_links:
                    # Try alternative selectors
                    job_links = await page.query_selector_all('div[class*="position-card"] a, div[class*="job-card"] a')

                logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links")

                # Collect unique job URLs
                job_urls = set()
                for link in job_links:
                    href = await link.get_attribute('href')
                    if href and '/positions/' in href:
                        if href.startswith('/'):
                            href = f"https://careers.airbnb.com{href}"
                        job_urls.add(href)

                logger.info(f"{self.COMPANY_NAME}: Processing {len(job_urls)} unique jobs")

                # Visit each job detail page
                for job_url in list(job_urls)[:40]:  # Limit to 40 jobs
                    try:
                        detail_page = await browser.new_page()
                        try:
                            await detail_page.goto(job_url, timeout=self.TIMEOUT)
                            await detail_page.wait_for_load_state("networkidle", timeout=15000)

                            # Extract title
                            title = await self.safe_get_text(detail_page, 'h1, h2, [class*="title"]')
                            if not title:
                                title = "Unknown Position"

                            # Extract location
                            location = await self.safe_get_text(detail_page, '[class*="location"]', 'Remote')

                            # Extract description
                            desc_element = await detail_page.query_selector('main, article, [class*="description"], [class*="content"]')
                            description = ""
                            if desc_element:
                                description = await desc_element.text_content() or ""
                                description = description.strip()

                            # Extract requirements
                            requirements = []

                            # Look for common Airbnb section headings
                            req_keywords = [
                                "what you'll do",
                                "what we're looking for",
                                "requirements",
                                "qualifications",
                                "what you'll bring"
                            ]

                            for keyword in req_keywords:
                                sections = await detail_page.query_selector_all(
                                    f'h2:has-text("{keyword}"), h3:has-text("{keyword}"), '
                                    f'h4:has-text("{keyword}"), strong:has-text("{keyword}")'
                                )
                                for section in sections[:2]:
                                    # Get the parent or next sibling to find list items
                                    try:
                                        parent = await section.evaluate_handle('el => el.parentElement || el.nextElementSibling')
                                        req_items = await parent.query_selector_all('li, p')
                                        for item in req_items[:15]:
                                            req_text = await item.text_content()
                                            if req_text and len(req_text.strip()) > 10:
                                                requirements.append(req_text.strip())
                                    except Exception:
                                        continue

                            # If no requirements found, extract from lists
                            if not requirements:
                                list_items = await detail_page.query_selector_all('ul li')
                                for item in list_items[:15]:
                                    req_text = await item.text_content()
                                    if req_text and len(req_text.strip()) > 10:
                                        requirements.append(req_text.strip())

                            # Extract posting date if available
                            posting_date = await self.safe_get_text(
                                detail_page,
                                '[class*="posted"], [class*="date"], time',
                                None
                            )

                            # Create job object
                            job = self.create_job_dict(
                                title=title,
                                description=description[:5000],
                                requirements=requirements[:15],
                                location=location,
                                url=job_url,
                                posting_date=posting_date
                            )

                            jobs.append(job)
                            logger.debug(f"{self.COMPANY_NAME}: Scraped job - {title}")

                        except Exception as e:
                            logger.warning(f"{self.COMPANY_NAME}: Error scraping job at {job_url}: {e}")
                        finally:
                            await detail_page.close()

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Could not process job URL {job_url}: {e}")
                        continue

            finally:
                await browser.close()
                logger.info(f"{self.COMPANY_NAME}: Browser closed")

        return jobs
