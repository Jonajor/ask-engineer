import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from .models import QueryRequest, QueryResponse, UploadResponse
from .rag import RAGEngine

# Ensure OPENAI_API_KEY is set
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Please set OPENAI_API_KEY environment variable.")

app = FastAPI(title="Strata Knowledge Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine: RAGEngine | None = None


@app.on_event("startup")
def startup_event():
    global rag_engine
    rag_engine = RAGEngine()


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    assert rag_engine is not None, "Engine not initialized"
    answer, sources = rag_engine.answer(
        question=req.question,
        history=req.history,
        report_id=req.report_id,
    )
    return QueryResponse(answer=answer, sources=sources)


@app.post("/upload-report", response_model=UploadResponse)
async def upload_report(file: UploadFile = File(...)):
    """
    Upload a PDF report so project managers can ask questions
    specifically about that document. In-memory only, no DB.
    """
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # 1) Read file bytes
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading uploaded file: {e}")

    # 2) Parse PDF with BytesIO (pypdf prefers a file-like)
    try:
        reader = PdfReader(io.BytesIO(content))
        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            full_text += page_text + "\n"
    except Exception as e:
        # This will show up in Streamlit instead of a generic 500
        raise HTTPException(status_code=400, detail=f"Error parsing PDF: {e}")

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="PDF appears to be empty or unreadable")

    # 3) Ingest into in-memory RAG engine (no DB)
    assert rag_engine is not None, "Engine not initialized"
    try:
        report_id = rag_engine.ingest_report(filename=file.filename, text=full_text)
    except Exception as e:
        # Likely an OpenAI / embeddings issue
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error ingesting report: {e}")

    return UploadResponse(report_id=report_id, filename=file.filename)

@app.get("/health")
def healthz():
    return {"status": "ok"}
