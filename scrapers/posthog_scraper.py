from typing import List, Dict
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PostHogScraper(BaseScraper):
    """Scraper for PostHog careers page"""

    COMPANY_NAME = "posthog"
    URL = "https://posthog.com/careers"
    # XPath provided by user - filter for "build products"
    ROLES_XPATH = '//*[@id="roles"]/div[1]/div/div[1]/div/div[2]/div/div/div/div/div[1]'

    async def scrape(self) -> List[Dict]:
        """Scrape job listings from PostHog careers page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")

                await page.goto(self.URL, timeout=self.TIMEOUT, wait_until="networkidle")
                logger.info(f"{self.COMPANY_NAME}: Page loaded successfully")

                # Wait for roles section to load
                await page.wait_for_selector('#roles', timeout=self.TIMEOUT)

                # Find the container using the provided XPath
                container = await page.query_selector(f'xpath={self.ROLES_XPATH}')

                if not container:
                    logger.warning(f"{self.COMPANY_NAME}: Container not found at XPath {self.ROLES_XPATH}")
                    return jobs

                # Check if container has "build products" text
                container_text = await container.text_content() or ""
                if "build products" not in container_text.lower():
                    logger.warning(f"{self.COMPANY_NAME}: Container doesn't contain 'build products', skipping")
                    return jobs

                logger.info(f"{self.COMPANY_NAME}: Found 'build products' section")

                # Find all job items within the container
                # PostHog likely uses cards or list items for jobs
                job_elements = await container.query_selector_all('a[href*="/careers/"]')

                if not job_elements:
                    # Try alternative selectors
                    job_elements = await container.query_selector_all('div[class*="job"], div[class*="position"]')

                logger.info(f"{self.COMPANY_NAME}: Found {len(job_elements)} job elements")

                for job_element in job_elements:
                    try:
                        # Extract job title
                        title_el = await job_element.query_selector('h3, h4, h5, strong, [class*="title"]')
                        title = await title_el.text_content() if title_el else "Unknown Position"
                        title = title.strip()

                        # Extract job URL
                        href = await job_element.get_attribute('href')
                        if not href:
                            # If parent is not a link, try finding a link child
                            link_el = await job_element.query_selector('a')
                            href = await link_el.get_attribute('href') if link_el else None

                        if not href:
                            logger.debug(f"{self.COMPANY_NAME}: No URL found for job {title}")
                            continue

                        # Make URL absolute if relative
                        if href.startswith('/'):
                            job_url = f"https://posthog.com{href}"
                        else:
                            job_url = href

                        # Extract location (if available)
                        location_el = await job_element.query_selector('[class*="location"], span:has-text("Remote")')
                        location = await location_el.text_content() if location_el else "Remote"
                        location = location.strip()

                        # Extract description from current element
                        description_el = await job_element.query_selector('p, [class*="description"]')
                        description = await description_el.text_content() if description_el else ""

                        # If description is short, navigate to job detail page
                        if len(description) < 100:
                            detail_page = await browser.new_page()
                            try:
                                await detail_page.goto(job_url, timeout=self.TIMEOUT)
                                await detail_page.wait_for_load_state("networkidle", timeout=10000)

                                # Extract full description
                                desc_content = await detail_page.query_selector('main, article, [class*="content"]')
                                if desc_content:
                                    description = await desc_content.text_content() or ""
                                    description = description.strip()

                                # Extract requirements
                                req_section = await detail_page.query_selector(
                                    'section:has-text("Requirements"), section:has-text("Qualifications"), ul'
                                )
                                requirements = []
                                if req_section:
                                    req_items = await req_section.query_selector_all('li')
                                    for item in req_items[:10]:  # Limit to first 10
                                        req_text = await item.text_content()
                                        if req_text:
                                            requirements.append(req_text.strip())

                            except Exception as e:
                                logger.debug(f"{self.COMPANY_NAME}: Could not load detail page for {title}: {e}")
                            finally:
                                await detail_page.close()
                        else:
                            requirements = []

                        # Create job object
                        job = self.create_job_dict(
                            title=title,
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
