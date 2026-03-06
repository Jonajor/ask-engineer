import json
import uuid
from typing import List, Dict, Tuple, Optional

import numpy as np
from fastembed import TextEmbedding
from groq import Groq

from knowledge_base import KNOWLEDGE_CHUNKS

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHAT_MODEL = "llama-3.3-70b-versatile"

_embedder: TextEmbedding | None = None
client = Groq()


def _get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(EMBEDDING_MODEL)
    return _embedder


def _normalize(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-10)


def _embed(texts: List[str]) -> List[np.ndarray]:
    if not texts:
        return []
    vectors = list(_get_embedder().embed(texts))
    return [_normalize(np.array(v, dtype="float32")) for v in vectors]


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
            if total > 20000:
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
            '  "executive_summary": "3-5 sentence plain-language summary of the overall building condition, '
            'key risks, and most urgent recommendations",\n'
            '  "building_overview": "key building facts: age, type, number of units, location, '
            'major systems (roofing, envelope, mechanical, electrical, parkade, elevators, etc.) and their general condition",\n'
            '  "top_priorities": [\n'
            '    {\n'
            '      "rank": 1,\n'
            '      "component": "component name",\n'
            '      "condition": "Good/Fair/Poor/Critical",\n'
            '      "urgency": "Immediate/Short-Term/Medium-Term/Long-Term",\n'
            '      "estimated_cost_range": "$X,XXX - $X,XXX or Not specified",\n'
            '      "recommended_action": "specific, actionable recommendation with rationale"\n'
            '    }\n'
            '  ],\n'
            '  "components_near_eol": [\n'
            '    {\n'
            '      "component": "name",\n'
            '      "estimated_remaining_life": "X years or At end of life",\n'
            '      "notes": "replacement cost estimate, urgency, and any interim maintenance needed"\n'
            '    }\n'
            '  ],\n'
            '  "funding_notes": "detailed observations about reserve fund balance, adequacy vs projected costs, '
            'recommended special levies or contribution increases if mentioned",\n'
            '  "escalation_items": ["specific item requiring engineer sign-off or professional assessment", ...]\n'
            "}\n\n"
            "Rules:\n"
            "- Include up to 8 top priorities, ranked by urgency and cost impact.\n"
            "- Include all components with less than 7 years of estimated remaining life.\n"
            "- recommended_action must be specific and actionable (e.g. 'Commission a Level 2 inspection by a licensed envelope engineer within 6 months'), not generic.\n"
            "- If information is not in the report, use 'Not specified' rather than guessing.\n"
            "- Flag any item requiring formal structural, legal, or engineering sign-off as an escalation item.\n"
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

    # ---------- REPORT IMPROVEMENT TIPS ----------

    def improve_report(self, report_id: str) -> dict:
        chunks = [d for d in self.report_docs if d.get("report_id") == report_id]
        if not chunks:
            return {
                "overall_score": "N/A",
                "summary": "No report content found for this report ID.",
                "tips": [],
                "missing_sections": [],
                "strengths": [],
            }

        text_blocks = []
        total = 0
        for c in chunks:
            text_blocks.append(c["text"])
            total += len(c["text"])
            if total > 20000:
                break
        report_text = "\n\n".join(text_blocks)

        system_prompt = (
            "You are a senior peer reviewer and quality assurance expert at Strata Engineering, "
            "a professional engineering firm in British Columbia. "
            "Your role is to review draft building condition assessments, depreciation reports, "
            "and warranty inspection reports before they are issued to clients. "
            "You provide detailed, constructive feedback to help engineers and technicians "
            "improve their reports to meet professional standards."
        )

        user_prompt = (
            "Review the following building report draft from the perspective of a senior engineer "
            "doing a quality check before the report is made official. "
            "Return a JSON object with exactly these fields:\n\n"
            "{\n"
            '  "overall_score": "X/10 with a one-line rationale",\n'
            '  "summary": "2-3 sentence overall assessment of the report quality",\n'
            '  "tips": [\n'
            '    {\n'
            '      "category": "one of: Completeness / Technical Accuracy / Clarity / Methodology / Recommendations / Documentation / Compliance",\n'
            '      "severity": "Critical / Recommended / Minor",\n'
            '      "issue": "specific problem found in the report",\n'
            '      "suggestion": "concrete, actionable improvement the author should make"\n'
            '    }\n'
            '  ],\n'
            '  "missing_sections": ["section or element that is absent but should be present in a professional report of this type"],\n'
            '  "strengths": ["specific thing the report does well"]\n'
            "}\n\n"
            "Review criteria:\n"
            "- Completeness: Are all building systems covered? Are costs, timelines, and photos referenced?\n"
            "- Technical Accuracy: Are findings consistent? Are standards (BC Building Code, ASTM, CSA) cited where needed?\n"
            "- Clarity: Is language precise and unambiguous? Could a non-engineer misinterpret any finding?\n"
            "- Methodology: Is the inspection scope and limitations clearly stated?\n"
            "- Recommendations: Are action items specific, prioritized, and tied to findings?\n"
            "- Documentation: Are assumptions, dates, access limitations, and exclusions noted?\n"
            "- Compliance: Are strata-specific requirements (SPA, Homeowner Protection Act) addressed if applicable?\n\n"
            "Include up to 10 tips, prioritized by severity. Be specific — reference actual content from the report.\n"
            "Return ONLY valid JSON, no extra text.\n\n"
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
                "overall_score": "N/A",
                "summary": "Could not parse improvement tips. Raw output: " + raw[:500],
                "tips": [],
                "missing_sections": [],
                "strengths": [],
            }
