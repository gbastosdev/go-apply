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

                await page.goto(self.URL, timeout=self.TIMEOUT, wait_until="networkidle")
                logger.info(f"{self.COMPANY_NAME}: Page loaded successfully")

                # Wait for job listings to appear (Ashby uses JavaScript rendering)
                # Try multiple possible selectors for Ashby
                try:
                    await page.wait_for_selector(
                        '[data-testid="job-card"], .ashby-job-posting-brief-list, a[href*="/jobs.ashbyhq.com/"]',
                        timeout=20000
                    )
                except Exception:
                    logger.warning(f"{self.COMPANY_NAME}: Standard selectors not found, trying alternative approach")

                # Find all job cards/links
                job_links = await page.query_selector_all('a[href*="jobs.ashbyhq.com/kraken.com"]')

                if not job_links:
                    # Alternative: find any links in the page that might be jobs
                    job_links = await page.query_selector_all('a[class*="job"], a[data-testid*="job"]')

                logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links")

                # Collect unique job URLs
                job_urls = set()
                for link in job_links:
                    href = await link.get_attribute('href')
                    if href and 'kraken.com' in href:
                        if href.startswith('/'):
                            href = f"https://jobs.ashbyhq.com{href}"
                        job_urls.add(href)

                logger.info(f"{self.COMPANY_NAME}: Processing {len(job_urls)} unique jobs")

                # Visit each job detail page
                for job_url in list(job_urls)[:50]:  # Limit to 50 jobs to avoid excessive time
                    try:
                        detail_page = await browser.new_page()
                        try:
                            await detail_page.goto(job_url, timeout=self.TIMEOUT)
                            await detail_page.wait_for_load_state("networkidle", timeout=15000)

                            # Extract title
                            title = await self.safe_get_text(detail_page, 'h1, h2, [class*="title"]')
                            if not title:
                                title = await self.safe_get_text(detail_page, '[data-testid="job-title"]', 'Unknown Position')

                            # Extract location
                            location = await self.safe_get_text(detail_page, '[class*="location"], [data-testid*="location"]', 'Remote')

                            # Extract description
                            desc_element = await detail_page.query_selector('main, article, [class*="description"], [class*="content"]')
                            description = ""
                            if desc_element:
                                description = await desc_element.text_content() or ""
                                description = description.strip()

                            # Extract requirements
                            requirements = []
                            # Look for sections containing requirements/qualifications
                            req_sections = await detail_page.query_selector_all(
                                'section:has-text("Requirements"), section:has-text("Qualifications"), '
                                'div:has-text("Requirements"), div:has-text("Qualifications")'
                            )

                            for section in req_sections[:2]:  # First 2 matching sections
                                req_items = await section.query_selector_all('li, p')
                                for item in req_items[:15]:  # Max 15 requirements
                                    req_text = await item.text_content()
                                    if req_text and len(req_text.strip()) > 10:
                                        requirements.append(req_text.strip())

                            # If no structured requirements, try to extract from description
                            if not requirements and description:
                                # Look for bullet points or numbered lists
                                lines = description.split('\n')
                                for line in lines:
                                    line = line.strip()
                                    if (line.startswith('•') or line.startswith('-') or
                                        line.startswith('*') or line[0:2].replace('.', '').isdigit()):
                                        if len(line) > 10:
                                            requirements.append(line.lstrip('•-*0123456789. '))

                            # Extract posting date if available
                            posting_date = await self.safe_get_text(
                                detail_page,
                                '[class*="posted"], [class*="date"], time',
                                None
                            )

                            # Create job object
                            job = self.create_job_dict(
                                title=title,
                                description=description[:5000],  # Limit length
                                requirements=requirements[:15],  # Max 15 requirements
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
