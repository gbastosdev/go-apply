import asyncio
from typing import Optional, List, Dict
from fastapi import HTTPException
from datetime import datetime
from services.file_storage_service import file_storage
from services.scheduler_service import scrape_all_jobs, scheduler_service
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def get_job_opportunities(
    company: Optional[str] = None,
    location: Optional[str] = None,
    tech_stack: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0
) -> Dict:
    """
    Get job opportunities from cache with optional filtering

    Args:
        company: Filter by company name (kraken, posthog, coinbase, railway, airbnb)
        location: Filter by location (case-insensitive partial match)
        tech_stack: Filter by technology (case-insensitive)
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)

    Returns:
        Standardized response with jobs and metadata

    Raises:
        HTTPException 404: No cached jobs available
        HTTPException 503: Cache service unavailable
    """
    try:
        # Fetch all jobs from file storage
        cached_jobs = await file_storage.get_all_jobs()

        if not cached_jobs:
            raise HTTPException(
                status_code=404,
                detail="No jobs available yet. Try refreshing with POST /api/job_opportunities/refresh"
            )

        # Apply filters
        filtered_jobs = apply_filters(cached_jobs, company, location, tech_stack)

        # Pagination
        total_filtered = len(filtered_jobs)
        if limit:
            paginated_jobs = filtered_jobs[offset:offset + limit]
        else:
            paginated_jobs = filtered_jobs[offset:]

        # Get metadata
        metadata = await file_storage.get_metadata()
        metadata["filtered_count"] = total_filtered

        logger.info(f"Returning {len(paginated_jobs)}/{total_filtered} jobs (filters: company={company}, location={location}, tech={tech_stack})")

        return {
            "status": "success",
            "data": {
                "jobs": paginated_jobs,
                "metadata": metadata
            }
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error retrieving jobs: {e}")
        raise HTTPException(
            status_code=503,
            detail="Storage service unavailable. Please try again later."
        )


async def refresh_jobs() -> Dict:
    """
    Trigger manual job refresh in background, return current data immediately

    Returns:
        Current data with refresh_in_progress flag

    Note: This returns current data instantly and triggers scraping in background
    """
    try:
        # Get current data
        cached_jobs = await file_storage.get_all_jobs()
        metadata = await file_storage.get_metadata()
        metadata["refresh_in_progress"] = True

        # Trigger background refresh
        asyncio.create_task(scrape_all_jobs())
        logger.info("Manual refresh triggered in background")

        return {
            "status": "success",
            "message": "Refresh triggered. This may take a few minutes. The data below is from the current storage.",
            "data": {
                "jobs": cached_jobs or [],
                "metadata": metadata
            }
        }

    except Exception as e:
        logger.error(f"Error triggering refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while triggering refresh. Please try again later."
        )


async def get_scraping_status() -> Dict:
    """
    Get detailed scraping status for all companies

    Returns:
        Status information including next scheduled run and company-specific status
    """
    try:
        metadata = await file_storage.get_metadata()

        # Get scheduler status
        scheduler_status = scheduler_service.get_status()

        # Get company-specific status
        companies_status = {}
        company_names = ["posthog", "kraken", "coinbase", "railway", "airbnb"]

        for company in company_names:
            status = await file_storage.get_scrape_status(company)
            if status:
                companies_status[company] = status
            else:
                # No status available
                companies_status[company] = {
                    "last_scraped": None,
                    "status": "unknown",
                    "job_count": 0,
                    "error": None
                }

        return {
            "status": "success",
            "data": {
                "scheduler": scheduler_status,
                "last_cache_update": metadata.get("cached_at"),
                "total_jobs_cached": metadata.get("total_count", 0),
                "companies": companies_status
            }
        }

    except Exception as e:
        logger.error(f"Error getting scraping status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal error while retrieving status. Please try again later."
        )


def apply_filters(
    jobs: List[Dict],
    company: Optional[str] = None,
    location: Optional[str] = None,
    tech_stack: Optional[str] = None
) -> List[Dict]:
    """
    Apply filters to job list

    Args:
        jobs: List of job dictionaries
        company: Company filter
        location: Location filter (case-insensitive partial match)
        tech_stack: Technology filter (case-insensitive)

    Returns:
        Filtered list of jobs
    """
    filtered = jobs

    # Filter by company
    if company:
        company_lower = company.lower()
        filtered = [j for j in filtered if j.get("company", "").lower() == company_lower]

    # Filter by location (partial match)
    if location:
        location_lower = location.lower()
        filtered = [j for j in filtered if location_lower in j.get("location", "").lower()]

    # Filter by tech stack
    if tech_stack:
        tech_lower = tech_stack.lower()
        filtered = [
            j for j in filtered
            if any(tech_lower in t.lower() for t in j.get("tech_stack", []))
        ]

    return filtered
