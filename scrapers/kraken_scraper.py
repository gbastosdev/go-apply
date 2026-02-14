from typing import List, Dict
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KrakenScraper(BaseScraper):
    """Scraper for Kraken careers (Ashby platform)"""

    COMPANY_NAME = "kraken"
    URL = "https://jobs.ashbyhq.com/kraken.com?departmentId=5f67bd79-103b-4ac1-8d79-952b45ea47c9&employmentType=FullTime&locationId=0ae979f7-78d9-4e42-8cf1-831610586017"

    async def scrape(self) -> List[Dict]:
        """Scrape job listings from Kraken Ashby careers page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")

                # Use domcontentloaded to avoid timeout issues
                await page.goto(self.URL, timeout=self.TIMEOUT, wait_until="domcontentloaded")
                logger.info(f"{self.COMPANY_NAME}: Page loaded")

                # Wait for content to load
                await page.wait_for_timeout(3000)

                # Find all job links - Ashby uses specific link patterns
                job_links = await page.query_selector_all('a[href*="/kraken.com/"]')
                logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links")

                # Collect job URLs and titles
                job_data = []
                for link in job_links:
                    try:
                        href = await link.get_attribute('href')
                        if not href:
                            continue

                        # Make URL absolute
                        if href.startswith('/'):
                            href = f"https://jobs.ashbyhq.com{href}"

                        # Get job title from link text
                        link_text = await link.text_content()
                        title = link_text.strip() if link_text else None

                        if title and href not in [j['url'] for j in job_data]:
                            job_data.append({
                                'url': href,
                                'title': title
                            })
                            logger.debug(f"{self.COMPANY_NAME}: Found job - {title}")

                    except Exception as e:
                        logger.debug(f"{self.COMPANY_NAME}: Error extracting link data: {e}")
                        continue

                logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs")

                # Visit each job detail page
                for job_info in job_data:
                    try:
                        detail_page = await browser.new_page()
                        try:
                            await detail_page.goto(job_info['url'], timeout=45000, wait_until="domcontentloaded")

                            # Wait for content
                            await detail_page.wait_for_timeout(2000)

                            # Extract location
                            location = await self.safe_get_text(
                                detail_page,
                                '[class*="location"], [data-testid*="location"]',
                                'Remote'
                            )

                            # Extract requirements from "The opportunity" and "Skills you should HODL"
                            requirements = []

                            try:
                                # Look for all headings
                                all_headings = await detail_page.query_selector_all('h1, h2, h3, h4, h5, h6')

                                target_headings = []
                                for heading in all_headings:
                                    text = await heading.text_content()
                                    if text:
                                        text_lower = text.lower()
                                        if 'the opportunity' in text_lower or 'skills you should hodl' in text_lower:
                                            target_headings.append(heading)

                                # Extract requirements from each target section
                                for heading in target_headings:
                                    # Get next sibling or parent's next sibling for the content
                                    next_element = await heading.evaluate_handle(
                                        'el => el.nextElementSibling || el.parentElement.nextElementSibling'
                                    )

                                    if next_element:
                                        # Look for list items or paragraphs
                                        req_items = await next_element.query_selector_all('li, p')
                                        for item in req_items:
                                            req_text = await item.text_content()
                                            if req_text and len(req_text.strip()) > 10:
                                                requirements.append(req_text.strip())

                            except Exception as e:
                                logger.warning(f"{self.COMPANY_NAME}: Error extracting requirements: {e}")

                            # Extract posting date if available
                            posting_date = await self.safe_get_text(
                                detail_page,
                                '[class*="posted"], [class*="date"], time',
                                None
                            )

                            # Create job object
                            job = self.create_job_dict(
                                title=job_info['title'],
                                requirements=requirements[:15],
                                location=location,
                                url=job_info['url'],
                                posting_date=posting_date
                            )

                            jobs.append(job)
                            logger.info(f"{self.COMPANY_NAME}: Scraped job - {job_info['title']} ({location}) - {len(requirements)} requirements")

                        except Exception as e:
                            logger.warning(f"{self.COMPANY_NAME}: Error scraping job at {job_info['url']}: {e}")
                        finally:
                            await detail_page.close()

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Could not process job: {e}")
                        continue

                await page.close()

            finally:
                await browser.close()
                logger.info(f"{self.COMPANY_NAME}: Browser closed")

        return jobs
