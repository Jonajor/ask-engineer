import uuid
from typing import List, Dict, Tuple, Optional

import numpy as np
from openai import OpenAI

from .knowledge_base import KNOWLEDGE_CHUNKS

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4.1-mini"

client = OpenAI()


def _normalize(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-10)


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
        # Base (static) knowledge
        self.base_docs: List[Dict] = KNOWLEDGE_CHUNKS
        self.base_embeddings: List[np.ndarray] = self._embed_texts(
            [d["text"] for d in self.base_docs]
        )

        # Dynamic report-specific chunks
        # Each doc: {id, title, text, report_id}
        self.report_docs: List[Dict] = []
        self.report_embeddings: List[np.ndarray] = []

    def _embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Embed a list of texts, return normalized vectors."""
        if not texts:
            return []

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        vectors = [
            _normalize(np.array(item.embedding, dtype="float32"))
            for item in response.data
        ]
        return vectors

    def _embed_query(self, query: str) -> np.ndarray:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[query],
        )
        v = np.array(response.data[0].embedding, dtype="float32")
        return _normalize(v)

    # ---------- REPORT INGESTION ----------

    def ingest_report(self, filename: str, text: str) -> str:
        """
        Ingest a report's full text:
        - chunk
        - embed each chunk
        - store with a new report_id
        """
        report_id = str(uuid.uuid4())
        chunks = chunk_text(text)

        if not chunks:
            return report_id

        vectors = self._embed_texts(chunks)

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

    def answer(
        self,
        question: str,
        history: List[Dict] | None = None,
        report_id: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        q_vec = self._embed_query(question)

        # If a report is specified, prioritize its chunks
        report_results: List[Dict] = []
        if report_id:
            report_results = self._retrieve_from_pool(
                q_vec,
                self.report_docs,
                self.report_embeddings,
                top_k=4,
                filter_report_id=report_id,
            )

        # Always also bring some generic knowledge
        base_results = self._retrieve_from_pool(
            q_vec,
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
            # Friendly source string
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
