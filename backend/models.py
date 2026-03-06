from pydantic import BaseModel
from typing import List, Optional


class QueryRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = None  # [{role, content}] optional chat history
    report_id: Optional[str] = None       # scope question to a specific report

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]

class UploadResponse(BaseModel):
    report_id: str
    filename: str

class PriorityItem(BaseModel):
    rank: int
    component: str
    condition: str
    urgency: str  # Immediate / Short-Term / Medium-Term / Long-Term
    estimated_cost_range: str
    recommended_action: str

class ComponentEOL(BaseModel):
    component: str
    estimated_remaining_life: str
    notes: str

class ReportAnalysis(BaseModel):
    executive_summary: str
    building_overview: str
    top_priorities: List[PriorityItem]
    components_near_eol: List[ComponentEOL]
    funding_notes: str
    escalation_items: List[str]


class ImprovementTip(BaseModel):
    category: str
    severity: str   # Critical / Recommended / Minor
    issue: str
    suggestion: str


class ReportImprovements(BaseModel):
    overall_score: str        # e.g. "7/10"
    summary: str
    tips: List[ImprovementTip]
    missing_sections: List[str]
    strengths: List[str]