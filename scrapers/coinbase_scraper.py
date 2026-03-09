import asyncio
import html
import re
from typing import List, Dict

import requests

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CoinbaseScraper(BaseScraper):
    COMPANY_NAME = "coinbase"
    # Greenhouse public API — no Selenium needed, no bot detection
    GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/coinbase/jobs?content=true"

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        logger.info(f"{self.COMPANY_NAME}: Fetching jobs from Greenhouse API")
        try:
            response = requests.get(self.GREENHOUSE_API, timeout=30)
            response.raise_for_status()
            all_jobs_raw = response.json().get("jobs", [])
        except Exception as e:
            logger.error(f"{self.COMPANY_NAME}: Failed to fetch from Greenhouse API: {e}")
            return []

        logger.info(f"{self.COMPANY_NAME}: Total jobs from API: {len(all_jobs_raw)}")

        # Filter: Engineering department + Brazil office
        eng_brazil = [
            j for j in all_jobs_raw
            if any("Engineering" in d.get("name", "") for d in j.get("departments", []))
            and any("Brazil" in o.get("name", "") for o in j.get("offices", []))
        ]

        logger.info(f"{self.COMPANY_NAME}: Engineering + Brazil jobs: {len(eng_brazil)}")

        jobs = []
        for raw in eng_brazil:
            try:
                title = raw.get("title", "Unknown Position")
                job_url = raw.get("absolute_url", "")
                location = raw.get("location", {}).get("name", "Remote - Brazil")

                # Extract requirements from HTML content
                content_html = html.unescape(raw.get("content", ""))
                requirements = self._extract_requirements(content_html)

                job = self.create_job_dict(
                    title=title,
                    requirements=requirements[:15],
                    location=location,
                    url=job_url,
                )
                jobs.append(job)
                logger.info(f"{self.COMPANY_NAME}: Scraped - {title} - {len(requirements)} reqs")

            except Exception as e:
                logger.warning(f"{self.COMPANY_NAME}: Error processing job '{raw.get('title')}': {e}")
                continue

        logger.info(f"{self.COMPANY_NAME}: Total jobs: {len(jobs)}")
        return jobs

    def _extract_requirements(self, content_html: str) -> List[str]:
        """Extract requirement bullet points from Greenhouse HTML job content."""
        # Strip tags helper
        def strip_tags(s: str) -> str:
            return re.sub(r"<[^>]+>", " ", s).strip()

        results = []
        # Look for sections with requirement-like headings
        req_keywords = [
            "what you'll do", "what you will do",
            "what you bring", "what you'll bring",
            "requirements", "qualifications",
            "minimum qualifications", "what we look for",
            "you have", "you will",
        ]

        # Split content into sections by headings
        # Find <li> elements within relevant sections
        sections = re.split(r"(?=<(?:h[1-6]|strong|b)\b)", content_html, flags=re.IGNORECASE)
        for section in sections:
            heading_match = re.match(r"<(?:h[1-6]|strong|b)[^>]*>(.*?)</(?:h[1-6]|strong|b)>", section, re.IGNORECASE | re.DOTALL)
            if heading_match:
                heading_text = strip_tags(heading_match.group(1)).lower()
                if any(kw in heading_text for kw in req_keywords):
                    # Extract all <li> items in this section
                    lis = re.findall(r"<li[^>]*>(.*?)</li>", section, re.IGNORECASE | re.DOTALL)
                    for li in lis:
                        text = strip_tags(li)
                        if len(text) > 10:
                            results.append(text)

        # Fallback: grab all <li> items if nothing found
        if not results:
            lis = re.findall(r"<li[^>]*>(.*?)</li>", content_html, re.IGNORECASE | re.DOTALL)
            for li in lis:
                text = strip_tags(li)
                if len(text) > 10:
                    results.append(text)

        return results
