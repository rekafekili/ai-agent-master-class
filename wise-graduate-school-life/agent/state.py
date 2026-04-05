from typing import Annotated
from operator import add

from typing_extensions import TypedDict


# ── 메인 그래프 State ────────────────────────────────────


class PaperState(TypedDict):
    file_path: str
    paper_id: str
    paper_title: str
    sections: list[dict]
    references_raw: str
    figures_tables: list[dict]
    vocabulary: Annotated[list[dict], add]
    summaries: Annotated[list[dict], add]
    reference_links: Annotated[list[dict], add]


# ── VocaManager 서브그래프 State ─────────────────────────


class VocaState(TypedDict):
    paper_id: str
    section: dict
    paragraphs: list[str]
    vocabulary: list[dict]


# ── TutorAgent 서브그래프 State ──────────────────────────


class TutorState(TypedDict):
    paper_id: str
    section: dict
    paragraphs: list[str]
    paragraph_summaries: list[dict]
    section_summary: str
    keywords: list[str]


# ── ReferenceHunter 서브그래프 State ─────────────────────


class ReferenceState(TypedDict):
    paper_id: str
    references_raw: str
    parsed_refs: list[dict]
    reference_links: list[dict]
