from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from agent.db import (
    get_connection,
    init_db,
    insert_reference_links,
    insert_summaries,
    insert_vocabulary,
)
from agent.state import PaperState
from tools.pdf_converter import convert_and_divide
from tools.vocabulary import voca_graph
from tools.tutor import tutor_graph
from tools.reference_hunter import reference_graph


# ── 래퍼 노드: 서브그래프 호출 + 메인 State 반환 ─────────


def run_voca_manager(state: dict) -> dict:
    """VocaManager 서브그래프를 실행하고 vocabulary를 메인 State에 반환."""
    result = voca_graph.invoke(
        {
            "paper_id": state["paper_id"],
            "section": state["section"],
        }
    )
    return {"vocabulary": result.get("vocabulary", [])}


def run_tutor_agent(state: dict) -> dict:
    """TutorAgent 서브그래프를 실행하고 summaries를 메인 State에 반환."""
    result = tutor_graph.invoke(
        {
            "paper_id": state["paper_id"],
            "section": state["section"],
        }
    )
    return {
        "summaries": [
            {
                "paper_id": state["paper_id"],
                "section_index": state["section"]["section_index"],
                "heading": state["section"]["heading"],
                "paragraph_summaries": result.get("paragraph_summaries", []),
                "section_summary": result.get("section_summary", ""),
                "keywords": result.get("keywords", []),
            }
        ]
    }


def run_reference_hunter(state: dict) -> dict:
    """ReferenceHunter 서브그래프를 실행하고 reference_links를 메인 State에 반환."""
    result = reference_graph.invoke(
        {
            "paper_id": state["paper_id"],
            "references_raw": state["references_raw"],
        }
    )
    return {"reference_links": result.get("reference_links", [])}


# ── 라우팅 + 저장 ───────────────────────────────────────


def route_to_subgraphs(state: PaperState) -> list[Send]:
    """convert_and_divide 결과를 3개 서브그래프로 병렬 fan-out."""
    sends = []

    for section in state["sections"]:
        sends.append(
            Send(
                "run_voca_manager",
                {
                    "paper_id": state["paper_id"],
                    "section": section,
                },
            )
        )
        sends.append(
            Send(
                "run_tutor_agent",
                {
                    "paper_id": state["paper_id"],
                    "section": section,
                },
            )
        )

    if state.get("references_raw"):
        sends.append(
            Send(
                "run_reference_hunter",
                {
                    "paper_id": state["paper_id"],
                    "references_raw": state["references_raw"],
                },
            )
        )

    return sends


def save_results(state: PaperState) -> dict:
    """모든 서브그래프 결과를 DB에 통합 저장."""
    print("[save_results] 노드 시작")
    conn = get_connection()
    init_db(conn)

    vocab_count = 0
    summary_count = 0
    ref_count = 0

    if state.get("vocabulary"):
        insert_vocabulary(conn, state["vocabulary"])
        vocab_count = len(state["vocabulary"])

    if state.get("summaries"):
        insert_summaries(conn, state["summaries"])
        summary_count = len(state["summaries"])

    if state.get("reference_links"):
        insert_reference_links(conn, state["reference_links"])
        ref_count = len(state["reference_links"])

    conn.close()
    print(
        f"[save_results] DB 저장 완료 — "
        f"단어 {vocab_count}개, 요약 {summary_count}개, 참고문헌 {ref_count}개"
    )
    return {}


# ── 메인 그래프 구성 ─────────────────────────────────────

graph_builder = StateGraph(PaperState)

graph_builder.add_node("convert_and_divide", convert_and_divide)
graph_builder.add_node("run_voca_manager", run_voca_manager)
graph_builder.add_node("run_tutor_agent", run_tutor_agent)
graph_builder.add_node("run_reference_hunter", run_reference_hunter)
graph_builder.add_node("save_results", save_results)

graph_builder.add_edge(START, "convert_and_divide")
graph_builder.add_conditional_edges(
    "convert_and_divide",
    route_to_subgraphs,
    ["run_voca_manager", "run_tutor_agent", "run_reference_hunter"],
)
graph_builder.add_edge("run_voca_manager", "save_results")
graph_builder.add_edge("run_tutor_agent", "save_results")
graph_builder.add_edge("run_reference_hunter", "save_results")
graph_builder.add_edge("save_results", END)

graph = graph_builder.compile()
