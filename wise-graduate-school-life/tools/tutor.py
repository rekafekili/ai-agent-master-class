"""TutorAgent 서브그래프 — 문단 분리 → 문단별 요약 → 섹션 종합 요약 + 키워드."""

import re

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from agent.prompts import (
    KEYWORD_EXTRACT_PROMPT,
    PARAGRAPH_SUMMARY_PROMPT,
    SECTION_SUMMARY_PROMPT,
)
from agent.state import TutorState

llm = init_chat_model("openai:gpt-4o-mini")


# ── Pydantic 스키마 ─────────────────────────────────────


class BilingualSummary(BaseModel):
    ko: str = Field(description="한국어 요약")
    en: str = Field(description="영어 요약")


class ParagraphSummaryResult(BaseModel):
    summary: BilingualSummary


class SectionSummaryResult(BaseModel):
    summary: BilingualSummary


class KeywordList(BaseModel):
    keywords: list[str] = Field(description="핵심 학술 키워드 5~10개")


para_summarizer = llm.with_structured_output(ParagraphSummaryResult)
section_summarizer = llm.with_structured_output(SectionSummaryResult)
keyword_extractor = llm.with_structured_output(KeywordList)


# ── 서브그래프 노드 ─────────────────────────────────────


def split_paragraphs(state: TutorState) -> dict:
    """섹션을 문단 단위로 분리."""
    content = state["section"]["content"]
    paragraphs = re.split(r"\n\s*\n", content.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]
    if not paragraphs:
        paragraphs = [content.strip()]

    heading = state["section"]["heading"]
    print(f"[TutorAgent:split_paragraphs] '{heading}' — {len(paragraphs)}개 문단")
    return {"paragraphs": paragraphs}


def summarize_paragraphs(state: TutorState) -> dict:
    """각 문단을 한영 병기로 요약."""
    heading = state["section"]["heading"]
    paragraphs = state["paragraphs"]

    print(f"[TutorAgent:summarize_paragraphs] '{heading}' — {len(paragraphs)}개 문단 요약 중...")

    paragraph_summaries = []
    for para in paragraphs:
        result = para_summarizer.invoke(
            PARAGRAPH_SUMMARY_PROMPT.format(paragraph=para)
        )
        paragraph_summaries.append({
            "ko": result.summary.ko,
            "en": result.summary.en,
        })

    print(f"[TutorAgent:summarize_paragraphs] '{heading}' 문단 요약 완료")
    return {"paragraph_summaries": paragraph_summaries}


def generate_section_summary(state: TutorState) -> dict:
    """문단 요약을 종합하여 섹션 요약 + 키워드 추출."""
    heading = state["section"]["heading"]
    paragraph_summaries = state["paragraph_summaries"]
    content = state["section"]["content"]

    print(f"[TutorAgent:generate_section_summary] '{heading}' 섹션 요약 생성 중...")

    # 섹션 종합 요약
    summaries_text = "\n\n".join(
        f"[문단 {i + 1}]\nEN: {ps['en']}\nKO: {ps['ko']}"
        for i, ps in enumerate(paragraph_summaries)
    )
    section_result = section_summarizer.invoke(
        SECTION_SUMMARY_PROMPT.format(
            heading=heading, paragraph_summaries=summaries_text
        )
    )
    section_summary = f"[EN] {section_result.summary.en}\n\n[KO] {section_result.summary.ko}"

    # 키워드 추출
    keyword_result = keyword_extractor.invoke(
        KEYWORD_EXTRACT_PROMPT.format(content=content)
    )

    print(
        f"[TutorAgent:generate_section_summary] '{heading}' 완료 — "
        f"{len(keyword_result.keywords)}개 키워드"
    )
    return {
        "section_summary": section_summary,
        "keywords": keyword_result.keywords,
    }


# ── 서브그래프 빌드 ─────────────────────────────────────


def build_tutor_graph():
    builder = StateGraph(TutorState)
    builder.add_node("split_paragraphs", split_paragraphs)
    builder.add_node("summarize_paragraphs", summarize_paragraphs)
    builder.add_node("generate_section_summary", generate_section_summary)
    builder.add_edge(START, "split_paragraphs")
    builder.add_edge("split_paragraphs", "summarize_paragraphs")
    builder.add_edge("summarize_paragraphs", "generate_section_summary")
    builder.add_edge("generate_section_summary", END)
    return builder.compile()


tutor_graph = build_tutor_graph()
