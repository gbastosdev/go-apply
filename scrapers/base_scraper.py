from abc import ABC, abstractmethod
from typing import List, Dict
import asyncio
import hashlib
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Page
from utils.logger import setup_logger
from services.tech_stack_extractor import TechStackExtractor

logger = setup_logger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for company-specific scrapers

    Provides:
    - Retry logic with exponential backoff
    - Browser lifecycle management (prevents memory leaks)
    - Timeout handling
    - Tech stack extraction
    - Job ID generation
    """

    TIMEOUT = 60000  # 60 seconds per page load
    MAX_RETRIES = 3
    COMPANY_NAME = "unknown"  # Override in subclass

    def __init__(self):
        self.tech_extractor = TechStackExtractor()

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        """
        Main scraping method - must be implemented by subclass

        Returns:
            List of job dictionaries with structure:
            {
                "id": str,
                "company": str,
                "title": str,
                "description": str,
                "requirements": List[str],
                "location": str,
                "posting_date": Optional[str],
                "tech_stack": List[str],
                "url": str,
                "scraped_at": datetime
            }
        """
        pass

    async def scrape_with_retry(self) -> List[Dict]:
        """
        Execute scraping with retry logic

        Returns:
            List of scraped jobs

        Raises:
            Exception if all retries exhausted
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"{self.COMPANY_NAME}: Starting scrape attempt {attempt}/{self.MAX_RETRIES}")
                jobs = await self.scrape()
                logger.info(f"{self.COMPANY_NAME}: Successfully scraped {len(jobs)} jobs")
                return jobs

            except PlaywrightTimeoutError as e:
                logger.warning(f"{self.COMPANY_NAME}: Timeout on attempt {attempt}: {e}")
                if attempt == self.MAX_RETRIES:
                    logger.error(f"{self.COMPANY_NAME}: All retries exhausted due to timeout")
                    raise
                await asyncio.sleep(5 * attempt)  # Exponential backoff

            except Exception as e:
                logger.error(f"{self.COMPANY_NAME}: Error on attempt {attempt}: {e}")
                if attempt == self.MAX_RETRIES:
                    logger.error(f"{self.COMPANY_NAME}: All retries exhausted")
                    raise
                await asyncio.sleep(5 * attempt)  # Exponential backoff

        return []

    def generate_job_id(self, title: str, company: str) -> str:
        """
        Generate unique job ID from title and company

        Args:
            title: Job title
            company: Company name

        Returns:
            Unique ID in format: {company}_{sanitized_title}_{hash}
        """
        # Sanitize title (remove special chars, lowercase, replace spaces)
        sanitized_title = "".join(c.lower() if c.isalnum() else "_" for c in title)
        sanitized_title = "_".join(filter(None, sanitized_title.split("_")))[:50]

        # Create hash for uniqueness
        hash_input = f"{company}_{title}".encode()
        hash_short = hashlib.md5(hash_input).hexdigest()[:8]

        return f"{company}_{sanitized_title}_{hash_short}"

    def extract_tech_stack(self, text: str) -> List[str]:
        """Extract technology stack from job description or requirements"""
        return self.tech_extractor.extract(text)

    def create_job_dict(
        self,
        title: str,
        description: str,
        requirements: List[str],
        location: str,
        url: str,
        posting_date: str = None
    ) -> Dict:
        """
        Create standardized job dictionary

        Args:
            title: Job title
            description: Full job description
            requirements: List of requirements/qualifications
            location: Job location
            url: Job posting URL
            posting_date: Optional posting date

        Returns:
            Standardized job dictionary
        """
        # Extract tech stack from description and requirements
        tech_text = f"{description} {' '.join(requirements)}"
        tech_stack = self.extract_tech_stack(tech_text)

        return {
            "id": self.generate_job_id(title, self.COMPANY_NAME),
            "company": self.COMPANY_NAME,
            "title": title,
            "description": description,
            "requirements": requirements,
            "location": location,
            "posting_date": posting_date,
            "tech_stack": tech_stack,
            "url": url,
            "scraped_at": datetime.now()
        }

    async def safe_get_text(self, page: Page, selector: str, default: str = "") -> str:
        """
        Safely get text content from element

        Args:
            page: Playwright page
            selector: CSS selector or XPath
            default: Default value if element not found

        Returns:
            Element text content or default
        """
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.text_content()
                return text.strip() if text else default
            return default
        except Exception as e:
            logger.debug(f"Could not get text for selector {selector}: {e}")
            return default

    async def safe_get_attribute(self, page: Page, selector: str, attribute: str, default: str = "") -> str:
        """
        Safely get attribute from element

        Args:
            page: Playwright page
            selector: CSS selector
            attribute: Attribute name (e.g., 'href')
            default: Default value if element not found

        Returns:
            Attribute value or default
        """
        try:
            element = await page.query_selector(selector)
            if element:
                value = await element.get_attribute(attribute)
                return value if value else default
            return default
        except Exception as e:
            logger.debug(f"Could not get attribute {attribute} for selector {selector}: {e}")
            return default
