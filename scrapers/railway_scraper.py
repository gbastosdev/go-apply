from typing import List, Dict
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RailwayScraper(BaseScraper):
    """Scraper for Railway careers page"""

    COMPANY_NAME = "railway"
    URL = "https://railway.com/careers#open-positions"

    async def scrape(self) -> List[Dict]:
        """Scrape job listings from Railway careers page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")

                await page.goto(self.URL, timeout=self.TIMEOUT, wait_until="networkidle")
                logger.info(f"{self.COMPANY_NAME}: Page loaded successfully")

                # Wait for the open-positions section to load
                try:
                    await page.wait_for_selector('#open-positions', timeout=20000)
                except Exception:
                    logger.warning(f"{self.COMPANY_NAME}: #open-positions selector not found")
                    # Continue anyway, might be accessible

                # Find job elements within the open-positions section
                # Try multiple possible selectors
                job_elements = await page.query_selector_all('#open-positions a[href*="/careers/"], #open-positions div[class*="position"]')

                if not job_elements:
                    # Try finding any job-related elements
                    job_elements = await page.query_selector_all('div[class*="job"], div[class*="position"], a[href*="apply"]')

                logger.info(f"{self.COMPANY_NAME}: Found {len(job_elements)} job elements")

                # Collect job information
                for job_element in job_elements:
                    try:
                        # Extract title
                        title_el = await job_element.query_selector('h2, h3, h4, [class*="title"]')
                        if not title_el:
                            # Try getting text directly from element
                            title = await job_element.text_content()
                            title = title.strip() if title else "Unknown Position"
                        else:
                            title = await title_el.text_content()
                            title = title.strip() if title else "Unknown Position"

                        # Skip if title is too short or generic
                        if len(title) < 5 or title.lower() in ['apply', 'learn more', 'view']:
                            continue

                        # Extract URL
                        href = await job_element.get_attribute('href')
                        if not href:
                            # If not a link itself, find link within
                            link_el = await job_element.query_selector('a')
                            href = await link_el.get_attribute('href') if link_el else None

                        if not href:
                            logger.debug(f"{self.COMPANY_NAME}: No URL for job {title}")
                            # Use careers page as fallback
                            job_url = self.URL
                        else:
                            # Make URL absolute
                            if href.startswith('/'):
                                job_url = f"https://railway.com{href}"
                            elif not href.startswith('http'):
                                job_url = f"https://railway.com/{href}"
                            else:
                                job_url = href

                        # Extract location
                        location_el = await job_element.query_selector('[class*="location"]')
                        location = await location_el.text_content() if location_el else "Remote"
                        location = location.strip() if location else "Remote"

                        # Extract description from current element
                        desc_el = await job_element.query_selector('p, [class*="description"]')
                        description = await desc_el.text_content() if desc_el else ""
                        description = description.strip() if description else ""

                        # If we have a valid job URL and short description, visit detail page
                        requirements = []
                        if job_url != self.URL and len(description) < 200:
                            detail_page = await browser.new_page()
                            try:
                                await detail_page.goto(job_url, timeout=self.TIMEOUT)
                                await detail_page.wait_for_load_state("networkidle", timeout=10000)

                                # Extract full description
                                desc_content = await detail_page.query_selector('main, article, [class*="content"]')
                                if desc_content:
                                    full_desc = await desc_content.text_content()
                                    description = full_desc.strip() if full_desc else description

                                # Extract requirements
                                req_sections = await detail_page.query_selector_all(
                                    'h2:has-text("Requirements"), h3:has-text("Requirements"), '
                                    'h2:has-text("Qualifications"), h3:has-text("Qualifications")'
                                )
                                for section in req_sections[:2]:
                                    parent = await section.evaluate_handle('el => el.parentElement')
                                    req_items = await parent.query_selector_all('li, p')
                                    for item in req_items[:15]:
                                        req_text = await item.text_content()
                                        if req_text and len(req_text.strip()) > 10:
                                            requirements.append(req_text.strip())

                            except Exception as e:
                                logger.debug(f"{self.COMPANY_NAME}: Could not load detail page for {title}: {e}")
                            finally:
                                await detail_page.close()

                        # Create job object
                        job = self.create_job_dict(
                            title=title,
                            description=description[:5000],
                            requirements=requirements,
                            location=location,
                            url=job_url,
                            posting_date=None
                        )

                        jobs.append(job)
                        logger.debug(f"{self.COMPANY_NAME}: Scraped job - {title}")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping individual job: {e}")
                        continue

            finally:
                await browser.close()
                logger.info(f"{self.COMPANY_NAME}: Browser closed")

        return jobs
