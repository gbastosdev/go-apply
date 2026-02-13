from typing import List, Dict
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CoinbaseScraper(BaseScraper):
    """Scraper for Coinbase careers (handles Engineering, Backend, Frontend departments)"""

    COMPANY_NAME = "coinbase"
    URLS = [
        "https://www.coinbase.com/pt-br/careers/positions?department=Engineering&location=remote",
        "https://www.coinbase.com/pt-br/careers/positions?department=Engineering+-+Backend&location=remote",
        "https://www.coinbase.com/pt-br/careers/positions?department=Engineering+-+Frontend&location=remote"
    ]

    async def scrape(self) -> List[Dict]:
        """Scrape job listings from all Coinbase engineering departments"""
        all_jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                # Scrape each department URL
                for url in self.URLS:
                    logger.info(f"{self.COMPANY_NAME}: Scraping {url}")
                    jobs = await self.scrape_department(browser, url)
                    all_jobs.extend(jobs)
                    logger.info(f"{self.COMPANY_NAME}: Found {len(jobs)} jobs from this department")

            finally:
                await browser.close()
                logger.info(f"{self.COMPANY_NAME}: Browser closed")

        # Remove duplicates based on job ID
        unique_jobs = {job['id']: job for job in all_jobs}.values()
        logger.info(f"{self.COMPANY_NAME}: Total unique jobs: {len(unique_jobs)}")

        return list(unique_jobs)

    async def scrape_department(self, browser, url: str) -> List[Dict]:
        """Scrape a single department page"""
        jobs = []

        page = await browser.new_page()
        try:
            await page.goto(url, timeout=self.TIMEOUT, wait_until="networkidle")
            logger.info(f"{self.COMPANY_NAME}: Page loaded - {url}")

            # Wait for job listings (Coinbase uses React, so wait for elements to render)
            try:
                await page.wait_for_selector(
                    'a[href*="/careers/position"], div[class*="position"], div[class*="job"]',
                    timeout=20000
                )
            except Exception:
                logger.warning(f"{self.COMPANY_NAME}: Could not find job selectors on {url}")
                return jobs

            # Find all job card elements
            job_elements = await page.query_selector_all('a[href*="/careers/position"]')

            if not job_elements:
                # Try alternative selectors
                job_elements = await page.query_selector_all('div[class*="position-card"], div[class*="job-card"]')

            logger.info(f"{self.COMPANY_NAME}: Found {len(job_elements)} job elements on page")

            # Collect job URLs
            job_urls = set()
            for element in job_elements:
                href = await element.get_attribute('href')
                if href:
                    if href.startswith('/'):
                        href = f"https://www.coinbase.com{href}"
                    job_urls.add(href)

            # Visit each job detail page
            for job_url in list(job_urls)[:40]:  # Limit to 40 jobs per department
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
                        location = await self.safe_get_text(detail_page, '[class*="location"]', 'Remote')

                        # Extract description
                        desc_element = await detail_page.query_selector('main, article, [class*="description"]')
                        description = ""
                        if desc_element:
                            description = await desc_element.text_content() or ""
                            description = description.strip()

                        # Extract requirements
                        requirements = []

                        # Look for sections with keywords
                        req_keywords = [
                            "what you'll bring",
                            "requirements",
                            "qualifications",
                            "what we look for",
                            "minimum qualifications"
                        ]

                        for keyword in req_keywords:
                            sections = await detail_page.query_selector_all(f'h2:has-text("{keyword}"), h3:has-text("{keyword}")')
                            for section in sections:
                                # Get the next sibling element (usually a ul or div)
                                parent = await section.evaluate_handle('el => el.parentElement')
                                req_items = await parent.query_selector_all('li, p')
                                for item in req_items[:15]:
                                    req_text = await item.text_content()
                                    if req_text and len(req_text.strip()) > 10:
                                        requirements.append(req_text.strip())

                        # If no requirements found, try generic list extraction
                        if not requirements:
                            list_items = await detail_page.query_selector_all('ul li')
                            for item in list_items[:15]:
                                req_text = await item.text_content()
                                if req_text and len(req_text.strip()) > 10:
                                    requirements.append(req_text.strip())

                        # Extract posting date if available
                        posting_date = await self.safe_get_text(detail_page, '[class*="posted"], time', None)

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

        except Exception as e:
            logger.error(f"{self.COMPANY_NAME}: Error scraping department {url}: {e}")
        finally:
            await page.close()

        return jobs
