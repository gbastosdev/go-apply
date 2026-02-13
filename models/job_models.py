from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
from datetime import datetime

class Job(BaseModel):
    """Individual job posting model"""
    id: str  # Format: {company}_{sanitized_title}_{hash}
    company: str  # kraken, posthog, coinbase, railway, airbnb
    title: str
    description: str
    requirements: List[str]  # Extracted bullet points or key requirements
    location: str
    posting_date: Optional[str] = None  # ISO format or "N days ago" or None
    tech_stack: List[str] = []  # Extracted technologies
    url: str  # Using str instead of HttpUrl for flexibility
    scraped_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CompanyMetadata(BaseModel):
    """Metadata for a single company's scraping results"""
    count: int
    last_scraped: datetime
    status: str  # "success", "failed", "pending"
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobsMetadata(BaseModel):
    """Metadata for entire job collection"""
    total_count: int
    filtered_count: int
    cached_at: datetime
    companies: Dict[str, CompanyMetadata]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobsData(BaseModel):
    """Data container for jobs response"""
    jobs: List[Job]
    metadata: JobsMetadata


class JobsResponse(BaseModel):
    """Standard API response for job opportunities"""
    status: str = "success"
    data: JobsData


class RefreshResponse(BaseModel):
    """Response for manual refresh endpoint"""
    status: str = "success"
    message: str
    data: JobsData


class StatusResponse(BaseModel):
    """Response for scraping status endpoint"""
    status: str = "success"
    data: Dict
