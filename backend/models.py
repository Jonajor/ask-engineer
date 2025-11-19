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