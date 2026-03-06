import json
import uuid
from typing import List, Dict, Tuple, Optional

import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer

from knowledge_base import KNOWLEDGE_CHUNKS

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHAT_MODEL = "llama-3.3-70b-versatile"

_embedder = SentenceTransformer(EMBEDDING_MODEL)
client = Groq()


def _normalize(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-10)


def _embed(texts: List[str]) -> List[np.ndarray]:
    if not texts:
        return []
    vectors = _embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.astype("float32") for v in vectors]


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    """Simple character-based chunking with overlap."""
    text = text.replace("\r\n", "\n")
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        chunk = text[start:end]
        chunks.append(chunk.strip())
        if end == length:
            break
        start = end - overlap
    return [c for c in chunks if c]


class RAGEngine:
    def __init__(self):
        self.base_docs: List[Dict] = KNOWLEDGE_CHUNKS
        self.base_embeddings: List[np.ndarray] = _embed(
            [d["text"] for d in self.base_docs]
        )

        self.report_docs: List[Dict] = []
        self.report_embeddings: List[np.ndarray] = []

    # ---------- REPORT INGESTION ----------

    def ingest_report(self, filename: str, text: str) -> str:
        report_id = str(uuid.uuid4())
        chunks = chunk_text(text)

        if not chunks:
            return report_id

        vectors = _embed(chunks)

        for chunk, vec in zip(chunks, vectors):
            doc = {
                "id": str(uuid.uuid4()),
                "title": f"Report: {filename}",
                "text": chunk,
                "report_id": report_id,
                "filename": filename,
            }
            self.report_docs.append(doc)
            self.report_embeddings.append(vec)

        return report_id

    # ---------- RETRIEVAL ----------

    def _retrieve_from_pool(
        self,
        query_vec: np.ndarray,
        docs: List[Dict],
        embeddings: List[np.ndarray],
        top_k: int = 3,
        filter_report_id: Optional[str] = None,
    ) -> List[Dict]:
        scored: List[Dict] = []

        for doc, vec in zip(docs, embeddings):
            if filter_report_id and doc.get("report_id") != filter_report_id:
                continue
            score = float(vec @ query_vec)
            scored.append({**doc, "score": score})

        scored.sort(key=lambda d: d["score"], reverse=True)
        return scored[:top_k]

    # ---------- ANSWER ----------

    def answer(
        self,
        question: str,
        history: List[Dict] | None = None,
        report_id: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        query_vec = _normalize(np.array(_embed([question])[0]))

        report_results: List[Dict] = []
        if report_id:
            report_results = self._retrieve_from_pool(
                query_vec,
                self.report_docs,
                self.report_embeddings,
                top_k=4,
                filter_report_id=report_id,
            )

        base_results = self._retrieve_from_pool(
            query_vec,
            self.base_docs,
            self.base_embeddings,
            top_k=2,
        )

        merged = report_results + base_results

        if not merged:
            context = "No relevant context found in the knowledge base."
        else:
            blocks = []
            for r in merged:
                src = r.get("filename") or r.get("title") or "Unknown source"
                blocks.append(f"[Source: {src}]\n{r['text']}")
            context = "\n\n---\n\n".join(blocks)

        sources: List[str] = []
        for r in merged:
            if "filename" in r:
                sources.append(f"{r.get('filename')} (report_id={r.get('report_id')})")
            else:
                sources.append(f"{r.get('title')} (id={r.get('id')})")

        system_prompt = (
            "You are a senior building science and strata engineering advisor. "
            "Your goal is to help PROJECT MANAGERS answer technical questions that "
            "they would normally ask an engineer or technician.\n\n"
            "Use ONLY the provided context from reports and knowledge base. "
            "Be conservative; if the question requires detailed structural analysis "
            "or legal advice, clearly say it must be escalated to an engineer.\n\n"
            "Always:\n"
            "- Explain in plain language first.\n"
            "- Then add a short technical note if needed.\n"
            "- Never give structural sign-off or legal advice."
        )

        if report_id:
            system_prompt += (
                "\n\nA specific report is associated with this question. "
                "Give priority to information coming from that report when answering."
            )

        user_prompt = (
            f"Question from project manager:\n{question}\n\n"
            f"Context from past reports and knowledge base:\n{context}\n\n"
            "Answer in a way that a project manager can forward parts of it to a strata "
            "council or property manager."
        )

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_prompt})

        chat = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
        )

        answer = chat.choices[0].message.content
        return answer, sources

    # ---------- REPORT ANALYSIS ----------

    def analyze_report(self, report_id: str) -> dict:
        chunks = [d for d in self.report_docs if d.get("report_id") == report_id]
        if not chunks:
            return {
                "executive_summary": "No report content found for this report ID.",
                "building_overview": "",
                "top_priorities": [],
                "components_near_eol": [],
                "funding_notes": "",
                "escalation_items": [],
            }

        text_blocks = []
        total = 0
        for c in chunks:
            text_blocks.append(c["text"])
            total += len(c["text"])
            if total > 12000:
                break
        report_text = "\n\n".join(text_blocks)

        system_prompt = (
            "You are a senior building science and strata engineering advisor at Strata Engineering, "
            "a professional engineering firm in British Columbia. "
            "You analyze depreciation reports and condition assessments for strata corporations. "
            "Your analysis is used by professional engineers and project managers."
        )

        user_prompt = (
            "Analyze the following building report excerpt and return a structured JSON object "
            "with exactly these fields:\n\n"
            "{\n"
            '  "executive_summary": "2-3 sentence plain-language summary of the building condition",\n'
            '  "building_overview": "key building facts extracted: age, type, location, major systems if mentioned",\n'
            '  "top_priorities": [\n'
            '    {\n'
            '      "rank": 1,\n'
            '      "component": "component name",\n'
            '      "condition": "Good/Fair/Poor/Critical",\n'
            '      "urgency": "Immediate/Short-Term/Medium-Term/Long-Term",\n'
            '      "estimated_cost_range": "$X,XXX - $X,XXX or Not specified",\n'
            '      "recommended_action": "concise action"\n'
            '    }\n'
            '  ],\n'
            '  "components_near_eol": [\n'
            '    {\n'
            '      "component": "name",\n'
            '      "estimated_remaining_life": "X years or At end of life",\n'
            '      "notes": "brief note"\n'
            '    }\n'
            '  ],\n'
            '  "funding_notes": "observations about reserve fund adequacy or funding concerns",\n'
            '  "escalation_items": ["item requiring engineer sign-off", ...]\n'
            "}\n\n"
            "Rules:\n"
            "- Include up to 5 top priorities, ranked by urgency and cost impact.\n"
            "- Include all components with less than 5 years of estimated remaining life.\n"
            "- If information is not in the report, use 'Not specified' rather than guessing.\n"
            "- Flag any item requiring formal structural or legal sign-off as an escalation item.\n"
            "- Return ONLY valid JSON, no extra text.\n\n"
            f"Report content:\n{report_text}"
        )

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "executive_summary": "Analysis could not be parsed. Raw output: " + raw[:500],
                "building_overview": "",
                "top_priorities": [],
                "components_near_eol": [],
                "funding_notes": "",
                "escalation_items": [],
            }
