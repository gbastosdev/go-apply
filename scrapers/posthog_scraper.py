import asyncio
from typing import List, Dict

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PostHogScraper(BaseScraper):
    COMPANY_NAME = "posthog"
    URL = "https://posthog.com/careers"
    # XPath to the main roles <ul> — confirmed by user
    ROLES_UL_XPATH = '//*[@id="roles"]/div[1]/div/div[1]/div/div[2]/div/div/div/div/div[1]/ul'

    async def scrape(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_scrape)

    def _sync_scrape(self) -> List[Dict]:
        jobs = []
        with self._browser() as browser:
            page = browser.new_page()
            try:
                logger.info(f"{self.COMPANY_NAME}: Navigating to {self.URL}")
                page.goto(self.URL, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                # Scroll to ensure all roles load (Next.js lazy rendering)
                for _ in range(4):
                    page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(800)
                page.evaluate("() => window.scrollTo(0, 0)")
                page.wait_for_timeout(500)

                job_links = self._collect_job_links(page)
                logger.info(f"{self.COMPANY_NAME}: Found {len(job_links)} job links")

                for href in job_links:
                    try:
                        page.goto(href, wait_until="domcontentloaded")
                        page.wait_for_timeout(1500)

                        try:
                            title = page.locator("h1").first.inner_text().strip()
                        except Exception:
                            title = ""

                        if not title:
                            logger.info(f"{self.COMPANY_NAME}: No h1 at {href}, skipping")
                            continue

                        requirements = page.evaluate("""() => {
                            const results = [];
                            const keywords = [
                                "what you'll work on", "what you'll do", "what you will do",
                                "what we're looking for", "who we're looking for", "who you are",
                                "requirements", "qualifications", "responsibilities",
                                "you have", "you bring", "you should", "you'll be",
                                "the role", "about the role"
                            ];
                            // Find a requirements-like heading, then grab its sibling LI items
                            const headings = document.querySelectorAll('h1,h2,h3,h4,h5,h6,strong');
                            let found = null;
                            for (const h of headings) {
                                const t = h.textContent.trim().toLowerCase();
                                if (keywords.some(k => t.includes(k))) { found = h; break; }
                            }
                            if (!found) return results;
                            // Walk siblings/ancestor siblings to find LI container
                            let el = found;
                            for (let d = 0; d < 5; d++) {
                                let sib = el.nextElementSibling;
                                while (sib) {
                                    const lis = sib.querySelectorAll('li');
                                    if (lis.length > 0) {
                                        for (const li of lis) {
                                            const t = li.textContent.trim();
                                            if (t.length > 15) results.push(t);
                                            if (results.length >= 20) return results;
                                        }
                                        return results;
                                    }
                                    sib = sib.nextElementSibling;
                                }
                                if (!el.parentElement) break;
                                el = el.parentElement;
                            }
                            return results;
                        }""") or []

                        description = page.evaluate("() => document.body.innerText") or ""

                        job = self.create_job_dict(
                            title=title,
                            requirements=requirements[:15],
                            location="Remote",
                            url=href,
                            description=description,
                        )
                        jobs.append(job)
                        logger.info(f"{self.COMPANY_NAME}: Scraped - {title} - {len(requirements)} reqs")

                    except Exception as e:
                        logger.warning(f"{self.COMPANY_NAME}: Error scraping {href}: {e}")
                        continue

            finally:
                logger.info(f"{self.COMPANY_NAME}: Done. Total: {len(jobs)}")

        return jobs

    def _collect_job_links(self, page) -> List[str]:
        """Find all 'Read more' links in the roles ul via XPath; fallback to page scan."""
        links = []

        # XPath strategy
        try:
            ul = page.locator(f"xpath={self.ROLES_UL_XPATH}")
            if ul.count() > 0:
                anchors = ul.first.locator("a")
                count = anchors.count()
                for i in range(count):
                    href = anchors.nth(i).get_attribute("href") or ""
                    if href and href not in links:
                        links.append(href if href.startswith("http") else f"https://posthog.com{href}")
                logger.info(f"{self.COMPANY_NAME}: XPath found {len(links)} links")
        except Exception as e:
            logger.warning(f"{self.COMPANY_NAME}: XPath strategy failed ({e})")

        if not links:
            # Fallback: page-wide /careers/<slug> scan
            links = page.evaluate("""() => {
                return [...new Set(
                    Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter(h => {
                            try {
                                const u = new URL(h);
                                return u.hostname.includes('posthog.com') &&
                                       /\\/careers\\/[a-z0-9-]+/.test(u.pathname);
                            } catch { return false; }
                        })
                )];
            }""") or []
            logger.info(f"{self.COMPANY_NAME}: Fallback found {len(links)} links")

        return links
