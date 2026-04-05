"""VocaManager 서브그래프 — 문단 분리 → 단어/관용구 추출."""

import re

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from agent.state import VocaState

llm = init_chat_model("openai:gpt-4o-mini")


# ── Pydantic 스키마 ─────────────────────────────────────


class VocabularyEntry(BaseModel):
    word: str = Field(description="영어 단어 또는 관용구/학술 표현")
    is_idiom: bool = Field(description="관용구/숙어/연어(collocation)이면 True, 단일 단어면 False")
    context_sentence: str = Field(description="논문에서 해당 단어/표현이 사용된 원문 문장")
    meaning_ko: str = Field(description="한국어 뜻")
    meaning_en: str = Field(description="영어 정의")


class VocabularyList(BaseModel):
    entries: list[VocabularyEntry] = Field(description="추출된 단어 및 관용구 목록")


extractor = llm.with_structured_output(VocabularyList)

EXTRACT_PROMPT = """다음 학술 논문 텍스트에서 대학원생이 알아야 할 핵심 영어 단어와 표현을 빠짐없이 추출하세요.
섹션의 길이에 비례하여 중요한 단어를 모두 포함합니다.

규칙:
- 일반적인 쉬운 단어(the, is, have 등)는 제외
- 학술 논문에서 자주 쓰이는 고급 어휘를 우선 선택
- 해당 분야의 전문 용어도 포함
- **관용구, 연어(collocation), 숙어(phrasal verb)도 포함** (예: "carry out", "in terms of", "account for")
- 각 항목이 단일 단어인지 관용구인지 is_idiom으로 표시
- 각 단어/표현이 논문에서 실제로 사용된 문장을 context_sentence로 포함

텍스트:
{content}
"""


# ── 서브그래프 노드 ─────────────────────────────────────


def split_paragraphs(state: VocaState) -> dict:
    """섹션을 문단 단위로 분리."""
    content = state["section"]["content"]
    paragraphs = re.split(r"\n\s*\n", content.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]
    if not paragraphs:
        paragraphs = [content.strip()]

    heading = state["section"]["heading"]
    print(f"[VocaManager:split_paragraphs] '{heading}' — {len(paragraphs)}개 문단")
    return {"paragraphs": paragraphs}


def extract_words(state: VocaState) -> dict:
    """각 문단에서 단어/관용구를 추출."""
    paper_id = state["paper_id"]
    section = state["section"]
    heading = section["heading"]
    section_index = section["section_index"]

    # 전체 섹션 content를 한번에 추출 (문단 정보는 컨텍스트로 활용)
    full_content = "\n\n".join(state["paragraphs"])
    print(f"[VocaManager:extract_words] '{heading}' 단어 추출 중...")

    result = extractor.invoke(EXTRACT_PROMPT.format(content=full_content))

    entries = []
    for entry in result.entries:
        entries.append({
            "paper_id": paper_id,
            "section_index": section_index,
            "word": entry.word,
            "is_idiom": entry.is_idiom,
            "context_sentence": entry.context_sentence,
            "meaning_ko": entry.meaning_ko,
            "meaning_en": entry.meaning_en,
        })

    print(f"[VocaManager:extract_words] '{heading}' 완료 — {len(entries)}개")
    return {"vocabulary": entries}


# ── 서브그래프 빌드 ─────────────────────────────────────


def build_voca_graph():
    builder = StateGraph(VocaState)
    builder.add_node("split_paragraphs", split_paragraphs)
    builder.add_node("extract_words", extract_words)
    builder.add_edge(START, "split_paragraphs")
    builder.add_edge("split_paragraphs", "extract_words")
    builder.add_edge("extract_words", END)
    return builder.compile()


voca_graph = build_voca_graph()
