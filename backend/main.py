import asyncio
import io
import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from auth import (
    authenticate_user, create_token, hash_password,
    get_current_user, require_superadmin, require_admin_or_above,
)
from db import get_db, init_db
from models import (
    QueryRequest, QueryResponse, UploadResponse, ReportAnalysis, ReportImprovements,
    LoginRequest, LoginResponse, CreateCompanyRequest, CreateUserRequest,
    CompanyInfo, UserInfo,
)
from rag import RAGEngine

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("Please set GROQ_API_KEY environment variable.")

app = FastAPI(title="Strata Knowledge Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine: RAGEngine | None = None


@app.on_event("startup")
async def startup_event():
    global rag_engine
    loop = asyncio.get_event_loop()
    rag_engine = await loop.run_in_executor(None, RAGEngine)


# ================================================================
# AUTH
# ================================================================

@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    result = authenticate_user(req.username, req.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if "error" in result:
        messages = {
            "account_disabled": "Your account has been disabled. Please contact support.",
            "company_inactive": "Your company's subscription is inactive. Please contact your administrator.",
            "trial_expired": "Your trial period has expired. Please contact your administrator.",
        }
        raise HTTPException(status_code=403, detail=messages.get(result["error"], "Access denied"))
    token = create_token(result)
    return LoginResponse(token=token, user=result)


@app.post("/auth/setup")
def setup_superadmin(req: CreateUserRequest):
    """One-time bootstrap: creates the superadmin if none exists."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'superadmin'")
            if cur.fetchone()[0] > 0:
                raise HTTPException(status_code=400, detail="Superadmin already exists")
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role, company_id) VALUES (%s, %s, %s, 'superadmin', NULL)",
                (req.username, req.email, hash_password(req.password)),
            )
        conn.commit()
    return {"message": "Superadmin created successfully"}


# ================================================================
# ADMIN — Companies
# ================================================================

@app.post("/admin/companies", response_model=CompanyInfo)
def create_company(req: CreateCompanyRequest, user=Depends(require_superadmin)):
    trial_ends_at = None
    if req.status == "trial":
        trial_ends_at = datetime.now(timezone.utc) + timedelta(days=req.trial_days)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO companies (name, slug, status, trial_ends_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, slug, status, trial_ends_at, created_at
            """, (req.name, req.slug, req.status, trial_ends_at))
            row = cur.fetchone()
        conn.commit()

    return CompanyInfo(
        id=str(row[0]), name=row[1], slug=row[2], status=row[3],
        trial_ends_at=row[4].isoformat() if row[4] else None,
        created_at=row[5].isoformat(),
    )


@app.get("/admin/companies", response_model=list[CompanyInfo])
def list_companies(user=Depends(require_superadmin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, slug, status, trial_ends_at, created_at FROM companies ORDER BY created_at DESC")
            rows = cur.fetchall()
    return [
        CompanyInfo(
            id=str(r[0]), name=r[1], slug=r[2], status=r[3],
            trial_ends_at=r[4].isoformat() if r[4] else None,
            created_at=r[5].isoformat(),
        )
        for r in rows
    ]


@app.patch("/admin/companies/{company_id}/status")
def update_company_status(company_id: str, status: str, user=Depends(require_superadmin)):
    if status not in ("trial", "active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be trial, active, or inactive")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE companies SET status = %s WHERE id = %s", (status, company_id))
        conn.commit()
    return {"message": f"Company status updated to {status}"}


# ================================================================
# ADMIN — Users
# ================================================================

@app.post("/admin/users", response_model=UserInfo)
def create_user(req: CreateUserRequest, user=Depends(get_current_user)):
    role = user.get("role")

    # Admins can only create regular users for their own company
    if role == "admin":
        if req.role != "user":
            raise HTTPException(status_code=403, detail="Admins can only create regular users")
        req.company_id = user["company_id"]
    elif role != "superadmin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if not req.company_id and role != "superadmin":
        raise HTTPException(status_code=400, detail="company_id is required")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, email, password_hash, role, company_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, username, email, role, is_active, company_id, created_at
            """, (req.username, req.email, hash_password(req.password), req.role, req.company_id or None))
            row = cur.fetchone()

            company_name = None
            if row[5]:
                cur.execute("SELECT name FROM companies WHERE id = %s", (str(row[5]),))
                r = cur.fetchone()
                company_name = r[0] if r else None
        conn.commit()

    return UserInfo(
        id=str(row[0]), username=row[1], email=row[2], role=row[3],
        is_active=row[4], company_id=str(row[5]) if row[5] else None,
        company_name=company_name, created_at=row[6].isoformat(),
    )


@app.get("/admin/users", response_model=list[UserInfo])
def list_users(user=Depends(get_current_user)):
    role = user.get("role")
    with get_db() as conn:
        with conn.cursor() as cur:
            if role == "superadmin":
                cur.execute("""
                    SELECT u.id, u.username, u.email, u.role, u.is_active, u.company_id, c.name, u.created_at
                    FROM users u LEFT JOIN companies c ON u.company_id = c.id
                    ORDER BY u.created_at DESC
                """)
            elif role == "admin":
                cur.execute("""
                    SELECT u.id, u.username, u.email, u.role, u.is_active, u.company_id, c.name, u.created_at
                    FROM users u LEFT JOIN companies c ON u.company_id = c.id
                    WHERE u.company_id = %s
                    ORDER BY u.created_at DESC
                """, (user["company_id"],))
            else:
                raise HTTPException(status_code=403, detail="Admin access required")
            rows = cur.fetchall()

    return [
        UserInfo(
            id=str(r[0]), username=r[1], email=r[2], role=r[3],
            is_active=r[4], company_id=str(r[5]) if r[5] else None,
            company_name=r[6], created_at=r[7].isoformat(),
        )
        for r in rows
    ]


@app.patch("/admin/users/{user_id}/toggle")
def toggle_user(user_id: str, user=Depends(get_current_user)):
    role = user.get("role")
    with get_db() as conn:
        with conn.cursor() as cur:
            if role == "superadmin":
                cur.execute("UPDATE users SET is_active = NOT is_active WHERE id = %s RETURNING is_active", (user_id,))
            elif role == "admin":
                cur.execute(
                    "UPDATE users SET is_active = NOT is_active WHERE id = %s AND company_id = %s RETURNING is_active",
                    (user_id, user["company_id"]),
                )
            else:
                raise HTTPException(status_code=403, detail="Admin access required")
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
    return {"is_active": row[0]}


# ================================================================
# REPORT ENDPOINTS (protected)
# ================================================================

@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, user=Depends(get_current_user)):
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="Engine is still initializing.")
    answer, sources = rag_engine.answer(
        question=req.question,
        history=req.history,
        report_id=req.report_id,
        viewer=user,
    )
    return QueryResponse(answer=answer, sources=sources)


@app.post("/upload-report", response_model=UploadResponse)
async def upload_report(file: UploadFile = File(...), user=Depends(get_current_user)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading uploaded file: {e}")
    try:
        reader = PdfReader(io.BytesIO(content))
        full_text = "".join((page.extract_text() or "") + "\n" for page in reader.pages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing PDF: {e}")
    if not full_text.strip():
        raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="Engine is still initializing.")
    try:
        report_id = rag_engine.ingest_report(
            filename=file.filename,
            text=full_text,
            company_id=user.get("company_id"),
            uploaded_by=user.get("user_id"),
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error ingesting report: {e}")
    return UploadResponse(report_id=report_id, filename=file.filename)


@app.post("/analyze-report/{report_id}", response_model=ReportAnalysis)
def analyze_report(report_id: str, user=Depends(get_current_user)):
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="Engine is still initializing.")
    result = rag_engine.analyze_report(report_id, viewer=user)
    return ReportAnalysis(**result)


@app.post("/improve-report/{report_id}", response_model=ReportImprovements)
def improve_report(report_id: str, user=Depends(get_current_user)):
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="Engine is still initializing.")
    result = rag_engine.improve_report(report_id, viewer=user)
    return ReportImprovements(**result)


@app.get("/health")
def healthz():
    return {"status": "ok"}
