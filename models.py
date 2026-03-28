from pydantic import BaseModel, Field
from typing import Optional

class Lead(BaseModel):
    title: str
    description: str
    budget: str
    location: str
    url: Optional[str] = None
    raw_html: Optional[str] = None

class ScoredLead(BaseModel):
    lead: Lead
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_signals: list[str]

class LeadOutput(BaseModel):
    scored_lead: ScoredLead
    pitch: Optional[str] = None  # Only if score > 0.8