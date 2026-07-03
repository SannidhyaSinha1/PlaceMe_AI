"""Company research agent: Tavily → FAISS → LangChain RetrievalQA + Groq.

Flow (implementation-rules #2 & #4):
  1. Check MongoDB `company_reports` cache — return immediately on hit.
  2. Else Tavily fetches up to 5 web results.
  3. Chunks embedded with HuggingFace all-MiniLM-L6-v2 → FAISS, persisted to
     ./faiss_indexes/{company}/ (reloaded if already present).
  4. RetrievalQA + Groq answers the four report sections.
  5. Report cached back into MongoDB.

Everything degrades: no Tavily key → no web docs; no LLM → template summary.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from functools import lru_cache

from ai_agents import llm_client
from fastapi_app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_SECTION_QUERIES = {
    "overview": "What does {c} do? Give a 3-sentence overview.",
    "tech_stack": "What is {c}'s main technology stack and engineering culture?",
    "interview_tips": "What are common interview questions and the hiring process at {c}?",
    "hiring_trends": "What roles and skills is {c} hiring for recently?",
}


def _safe_name(company: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", company.strip()) or "unknown"


@lru_cache(maxsize=1)
def _embeddings():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    except Exception as exc:  # pragma: no cover - heavy optional dep
        logger.warning("Embeddings unavailable: %s", exc)
        return None


def _tavily_search(company: str) -> tuple[list[str], list[str]]:
    if not settings.tavily_api_key:
        return [], []
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        res = client.search(
            query=f"{company} company overview tech stack hiring interview process",
            max_results=5,
            search_depth="advanced",
        )
        docs = [r.get("content", "") for r in res.get("results", []) if r.get("content")]
        urls = [r.get("url", "") for r in res.get("results", []) if r.get("url")]
        return docs, urls
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tavily search failed for %s: %s", company, exc)
        return [], []


def _build_vectorstore(company: str, docs: list[str]):
    embeddings = _embeddings()
    if embeddings is None or not docs:
        return None
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS

    index_path = os.path.join(settings.faiss_index_dir, _safe_name(company))
    if os.path.isdir(index_path):
        try:
            return FAISS.load_local(
                index_path, embeddings, allow_dangerous_deserialization=True
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("FAISS reload failed (%s); rebuilding", exc)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.create_documents(docs)
    vs = FAISS.from_documents(chunks, embeddings)
    os.makedirs(settings.faiss_index_dir, exist_ok=True)
    vs.save_local(index_path)
    return vs


def _generate_report(company: str, vectorstore, docs: list[str]) -> dict:
    sections = {}
    if vectorstore is not None and llm_client.llm_available():
        try:
            from langchain.chains import RetrievalQA

            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            for key, q in _SECTION_QUERIES.items():
                def build(llm, _retriever=retriever):
                    return RetrievalQA.from_chain_type(llm=llm, retriever=_retriever)

                ans = llm_client.invoke_with_fallback(
                    None, {"query": q.format(c=company), "_build": build}
                )
                sections[key] = ans["result"] if isinstance(ans, dict) else str(ans)
            return sections
        except Exception as exc:  # noqa: BLE001
            logger.warning("RetrievalQA failed for %s: %s", company, exc)

    # Fallback: stitch raw search snippets into each section.
    snippet = " ".join(docs)[:600] if docs else "No web data available."
    return {key: snippet for key in _SECTION_QUERIES}


async def research_company(company: str, opportunity_id: int | None = None) -> dict:
    """Return a structured report dict; MongoDB-cached by company name."""
    from fastapi_app.core.database import mongo_collection

    reports = mongo_collection("company_reports")
    if reports is not None:
        cached = await reports.find_one({"company_name": company})
        if cached:
            cached.pop("_id", None)
            cached["cached"] = True
            return cached

    # Web search, FAISS/embedding build and the LLM report are all blocking.
    import asyncio

    docs, urls = await asyncio.to_thread(_tavily_search, company)
    vectorstore = await asyncio.to_thread(_build_vectorstore, company, docs)
    sections = await asyncio.to_thread(_generate_report, company, vectorstore, docs)

    report = {
        "company_name": company,
        "company": company,
        "opportunity_id": opportunity_id,
        "overview": sections.get("overview", ""),
        "tech_stack": sections.get("tech_stack", ""),
        "interview_tips": sections.get("interview_tips", ""),
        "hiring_trends": sections.get("hiring_trends", ""),
        "sources": urls,
        "generated_at": datetime.now(UTC).isoformat(),
        "cached": False,
    }

    if reports is not None:
        try:
            await reports.update_one(
                {"company_name": company}, {"$set": report}, upsert=True
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Caching company report failed: %s", exc)
    return report
