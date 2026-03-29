from langchain.chat_models import init_chat_model
from langgraph.types import interrupt, Command
from pydantic import BaseModel, Field

from agent.db import get_connection, init_db, insert_vocabulary
from agent.state import PaperState

llm = init_chat_model("openai:gpt-4o")


class VocabularyEntry(BaseModel):
    word: str = Field(description="영어 단어 또는 학술 표현")
    context_sentence: str = Field(description="논문에서 해당 단어가 사용된 원문 문장")
    meaning_ko: str = Field(description="한국어 뜻")
    meaning_en: str = Field(description="영어 정의")


class VocabularyList(BaseModel):
    entries: list[VocabularyEntry] = Field(description="추출된 단어 목록")


extractor = llm.with_structured_output(VocabularyList)

EXTRACT_PROMPT = """다음 학술 논문 텍스트에서 대학원생이 알아야 할 핵심 영어 단어와 학술 표현을 10개 추출하세요.

규칙:
- 일반적인 쉬운 단어(the, is, have 등)는 제외
- 학술 논문에서 자주 쓰이는 고급 어휘와 표현을 우선 선택
- 해당 분야의 전문 용어도 포함
- 각 단어가 논문에서 실제로 사용된 문장을 context_sentence로 포함

텍스트:
{content}
"""


def extract_vocabulary(state: PaperState) -> PaperState:
    """각 섹션에서 핵심 영어 단어를 추출하는 노드. (DB 저장은 하지 않음)"""
    print("[extract_vocabulary] 노드 시작")
    paper_id = state["paper_id"]
    sections = state["sections"]
    total = len(sections)
    print(f"[extract_vocabulary] 총 {total}개 섹션에서 단어 추출 예정")

    all_entries = []
    for i, s in enumerate(sections):
        print(f"[extract_vocabulary] [{i + 1}/{total}] '{s['heading']}' 단어 추출 중...")
        result = extractor.invoke(
            EXTRACT_PROMPT.format(content=s["content"])
        )
        for entry in result.entries:
            all_entries.append({
                "paper_id": paper_id,
                "section_index": s["section_index"],
                "word": entry.word,
                "context_sentence": entry.context_sentence,
                "meaning_ko": entry.meaning_ko,
                "meaning_en": entry.meaning_en,
            })
        print(f"[extract_vocabulary] [{i + 1}/{total}] '{s['heading']}' 완료 — {len(result.entries)}개 단어")

    print(f"[extract_vocabulary] 추출 완료 — 총 {len(all_entries)}개 단어")
    return {"vocabulary": all_entries}


def human_review(state: PaperState) -> Command:
    """추출된 단어를 사용자에게 보여주고, 저장 여부를 interrupt로 입력받는 노드."""
    print("[human_review] 노드 시작 — 사용자 입력 대기 중")
    vocabulary = state["vocabulary"]

    answer = interrupt({
        "message": f"{len(vocabulary)}개 단어가 추출되었습니다. DB에 저장하시겠습니까?",
        "vocabulary_preview": [
            f"[섹션 {v['section_index']}] {v['word']} — {v['meaning_ko']}"
            for v in vocabulary[:20]
        ],
        "instruction": "save=True로 저장, save=False로 건너뛰기",
    })

    if answer.get("save", False):
        print("[human_review] 사용자 선택: 저장")
        return Command(goto="save_vocabulary")
    else:
        print("[human_review] 사용자 선택: 건너뛰기")
        return Command(goto="__end__")


def save_vocabulary(state: PaperState) -> PaperState:
    """추출된 단어를 DB에 저장하는 노드."""
    print("[save_vocabulary] 노드 시작")
    entries = state["vocabulary"]

    conn = get_connection()
    init_db(conn)
    insert_vocabulary(conn, entries)
    conn.close()

    print(f"[save_vocabulary] DB 저장 완료 — {len(entries)}개 단어")
    return {}
