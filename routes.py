from fastapi import HTTPException, status, UploadFile, File, Form, FastAPI, Query
from controllers import rag_controller, jobs_controller
from typing import Optional
import pdfplumber
import re

router = FastAPI()

@router.post("/resume")
async def upload_file_endpoint(cv: UploadFile = File(...), opportunity: str = Form(...)):
    """Process the opportunity and CV upload"""
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'opportunity' field is required."
        )

    if cv.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed."
        )

    try:
        with pdfplumber.open(cv.file) as pdf:
            contents = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
        contents = re.sub(
            r'(?i)(experiência|experiencia|experience|formação|formacao|education|habilidades|skills|projetos|projects|certificações|certifications)',
            r'\n### \1\n',
            contents
        )
        response = rag_controller.analyze_job_cv(opportunity, contents)
        return response

    except HTTPException as e:
        # Re-raise already handled errors
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while processing the file. Please try again later."
        )


@router.get("/job_opportunities")
async def get_job_opportunities_endpoint(
    company: Optional[str] = Query(None, description="Filter by company (kraken, posthog, coinbase, railway, airbnb)"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    tech_stack: Optional[str] = Query(None, description="Filter by technology"),
    limit: Optional[int] = Query(None, description="Maximum number of results", ge=1),
    offset: int = Query(0, description="Number of results to skip", ge=0)
):
    """
    Get job opportunities from cache with optional filtering

    Returns cached job listings from Kraken, PostHog, Coinbase, Railway, and Airbnb
    """
    return await jobs_controller.get_job_opportunities(company, location, tech_stack, limit, offset)


@router.post("/job_opportunities/refresh")
async def refresh_jobs_endpoint():
    """
    Manually trigger job scraping refresh

    Returns current cached data immediately and triggers background refresh
    """
    return await jobs_controller.refresh_jobs()


@router.get("/job_opportunities/status")
async def get_scraping_status_endpoint():
    """
    Get detailed scraping status

    Returns information about scheduler, last scrape time, and company-specific status
    """
    return await jobs_controller.get_scraping_status()