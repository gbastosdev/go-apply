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

                # Navigate to page with increased timeout
                await page.goto(self.URL, timeout=self.TIMEOUT, wait_until="domcontentloaded")
                logger.info(f"{self.COMPANY_NAME}: Page loaded")

                # Wait for content to load
                await page.wait_for_timeout(3000)

                # Find all job links
                job_links = await page.query_selector_all('a[href*="/careers/"]')
                logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links")

                # Collect job URLs and titles
                job_data = []
                for link in job_links:
                    try:
                        href = await link.get_attribute('href')
                        if not href or href == '/careers':  # Skip the main careers link
                            continue

                        # Make URL absolute
                        if href.startswith('/'):
                            href = f"https://railway.com{href}"

                        # Get job title from link text
                        link_text = await link.text_content()
                        title = link_text.strip() if link_text else None

                        if title and href not in [j['url'] for j in job_data]:
                            # Default location is Remote
                            location = "Remote"

                            # Check if title contains location patterns
                            if "Anywhere" in title:
                                location = "Anywhere"
                                title = title.replace("Anywhere", "").strip()
                            elif "Remote" in title:
                                location = "Remote"
                                title = title.replace("Remote", "").strip()
                            elif "Hybrid" in title:
                                location = "Hybrid"
                                title = title.replace("Hybrid", "").strip()

                            # Clean up title
                            title = title.rstrip(': -')

                            job_data.append({
                                'url': href,
                                'title': title,
                                'location': location
                            })
                            logger.debug(f"{self.COMPANY_NAME}: Found job - {title} ({location})")

                    except Exception as e:
                        logger.debug(f"{self.COMPANY_NAME}: Error extracting link data: {e}")
                        continue

                logger.info(f"{self.COMPANY_NAME}: Collected {len(job_data)} unique jobs")

                # Visit each job detail page
                for job_info in job_data:
                    try:
                        detail_page = await browser.new_page()
                        try:
                            # Use domcontentloaded instead of networkidle to avoid timeout
                            await detail_page.goto(job_info['url'], timeout=45000, wait_until="domcontentloaded")

                            # Wait for content
                            await detail_page.wait_for_timeout(2000)

                            # Extract requirements from "About you" section
                            requirements = []

                            try:
                                # Railway uses <p id="about-you"> followed by <li> elements until <p id="things-to-know">
                                # Use JavaScript to collect all <li> elements between these two paragraphs
                                requirements_js = await detail_page.evaluate('''
                                    () => {
                                        const requirements = [];
                                        const aboutYou = document.getElementById('about-you');

                                        if (!aboutYou) return requirements;

                                        let current = aboutYou.nextElementSibling;

                                        // Collect all <li> elements until we hit "things-to-know" or run out of siblings
                                        while (current) {
                                            // Stop if we hit "things-to-know" paragraph
                                            if (current.id === 'things-to-know') {
                                                break;
                                            }

                                            // Collect <li> elements
                                            if (current.tagName === 'LI') {
                                                const text = current.textContent.trim();
                                                if (text.length > 10) {
                                                    requirements.push(text);
                                                }
                                            }

                                            current = current.nextElementSibling;
                                        }

                                        return requirements;
                                    }
                                ''')

                                requirements.extend(requirements_js)

                            except Exception as e:
                                logger.warning(f"{self.COMPANY_NAME}: Error extracting requirements: {e}")

                            # Create job object
                            job = self.create_job_dict(
                                title=job_info['title'],
                                requirements=requirements[:15],
                                location=job_info['location'],
                                url=job_info['url'],
                                posting_date=None
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

                await page.close()

            finally:
                await browser.close()
                logger.info(f"{self.COMPANY_NAME}: Browser closed")

        return jobs
