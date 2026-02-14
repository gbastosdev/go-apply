from typing import List, Dict
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AirbnbScraper(BaseScraper):
    """Scraper for Airbnb careers page (Engineering department, Brazil only)"""

    COMPANY_NAME = "airbnb"
    # URL already filtered for Brazil engineering positions
    BASE_URL = "https://careers.airbnb.com/positions/?_departments=engineering&_where_you_work=brazil-63869%2Csao-paulo-brazil-176"

    async def scrape(self) -> List[Dict]:
        """Scrape job listings from Airbnb Brazil engineering careers page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                # Scrape both pages
                for page_num in [1, 2]:
                    url = f"{self.BASE_URL}&page={page_num}" if page_num > 1 else self.BASE_URL
                    logger.info(f"{self.COMPANY_NAME}: Scraping page {page_num} - {url}")

                    page_jobs = await self.scrape_page(browser, url, page_num)
                    jobs.extend(page_jobs)
                    logger.info(f"{self.COMPANY_NAME}: Found {len(page_jobs)} jobs on page {page_num}")

            finally:
                await browser.close()
                logger.info(f"{self.COMPANY_NAME}: Browser closed")

        logger.info(f"{self.COMPANY_NAME}: Total jobs scraped: {len(jobs)}")
        return jobs

    async def scrape_page(self, browser, url: str, page_num: int) -> List[Dict]:
        """Scrape a single page of job listings"""
        jobs = []

        page = await browser.new_page()
        try:
            await page.goto(url, timeout=self.TIMEOUT, wait_until="networkidle")
            logger.info(f"{self.COMPANY_NAME}: Page {page_num} loaded successfully")

            # Wait for page to be fully loaded
            await page.wait_for_timeout(2000)

            # Find all job links (they go to /positions/...)
            job_links = await page.query_selector_all('a[href*="/positions/"]')
            logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links on page {page_num}")

            # Collect job URLs and basic info
            job_data = []
            for link in job_links:
                try:
                    href = await link.get_attribute('href')
                    if not href or '/positions/?_' in href:  # Skip filter links
                        continue

                    # Make URL absolute
                    if href.startswith('/'):
                        href = f"https://careers.airbnb.com{href}"

                    # Get the link text (job title)
                    link_text = await link.text_content()
                    title = link_text.strip() if link_text else None

                    if title and href not in [j['url'] for j in job_data]:
                        # Try to get location from nearby text
                        parent = await link.evaluate_handle('el => el.parentElement')
                        parent_text = await parent.text_content()

                        # Extract hiring type (look for keywords)
                        location = "Remote"
                        if "Hybrid" in parent_text:
                            # Extract the hiring type after •
                            if "•" in parent_text:
                                parts = parent_text.split("•")
                                if len(parts) >= 2:
                                    location = parts[1].strip()
                                    # Remove the job title if it's in there
                                    if title in location:
                                        location = location.replace(title, "").strip()

                        job_data.append({
                            'url': href,
                            'title': title,
                            'location': location
                        })
                        logger.debug(f"{self.COMPANY_NAME}: Found job - {title} ({location})")

                except Exception as e:
                    logger.debug(f"{self.COMPANY_NAME}: Error extracting link data: {e}")
                    continue

            logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs on page {page_num}")

            # Visit each job detail page
            for job_info in job_data:
                try:
                    detail_page = await browser.new_page()
                    try:
                        await detail_page.goto(job_info['url'], timeout=self.TIMEOUT)
                        await detail_page.wait_for_load_state("networkidle", timeout=30000)

                        # Extract requirements from "Your Expertise" section
                        requirements = []

                        # Look for "Your Expertise" section
                        expertise_sections = await detail_page.query_selector_all(
                            'h2:has-text("Your Expertise"), h3:has-text("Your Expertise"), '
                            'h4:has-text("Your Expertise"), strong:has-text("Your Expertise")'
                        )

                        for section in expertise_sections:
                            try:
                                # Get the next sibling or parent element containing the list
                                next_element = await section.evaluate_handle(
                                    'el => el.nextElementSibling || el.parentElement.nextElementSibling'
                                )
                                req_items = await next_element.query_selector_all('li, p')
                                for item in req_items:
                                    req_text = await item.text_content()
                                    if req_text and len(req_text.strip()) > 10:
                                        requirements.append(req_text.strip())
                            except Exception:
                                continue

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
                            location=job_info['location'],
                            url=job_info['url'],
                            posting_date=posting_date
                        )

                        jobs.append(job)
                        logger.info(f"{self.COMPANY_NAME}: Scraped job - {job_info['title']} ({job_info['location']}) - {len(requirements)} requirements")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping job at {job_info['url']}: {e}")
                    finally:
                        await detail_page.close()

                except Exception as e:
                    logger.warning(f"{self.COMPANY_NAME}: Could not process job: {e}")
                    continue

        except Exception as e:
            logger.error(f"{self.COMPANY_NAME}: Error scraping page {page_num}: {e}")
        finally:
            await page.close()

        return jobs
