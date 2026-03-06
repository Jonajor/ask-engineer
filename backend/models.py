from pydantic import BaseModel
from typing import List, Optional, Dict, Any


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
    overall_score: str
    summary: str
    tips: List[ImprovementTip]
    missing_sections: List[str]
    strengths: List[str]


# ── Auth & Admin models ───────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]

class CreateCompanyRequest(BaseModel):
    name: str
    slug: str
    status: str = "trial"
    trial_days: int = 14

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"
    company_id: Optional[str] = None

class CompanyInfo(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    trial_ends_at: Optional[str]
    created_at: str

class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    company_id: Optional[str]
    company_name: Optional[str]
    created_at: str