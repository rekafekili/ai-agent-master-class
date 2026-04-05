"""ReferenceHunter 서브그래프 — 참고문헌 파싱 → 목록 출력."""

import re

from langgraph.graph import StateGraph, START, END

from agent.state import ReferenceState


# ── 서브그래프 노드 ─────────────────────────────────────


def parse_references(state: ReferenceState) -> dict:
    """References 원문에서 개별 문헌을 파싱하여 목록으로 반환."""
    references_raw = state["references_raw"]
    paper_id = state["paper_id"]
    print("[ReferenceHunter:parse_references] 참고문헌 파싱 시작...")

    refs = []
    lines = references_raw.strip().split("\n")
    current_ref = ""
    ref_index = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 새 참고문헌 시작 감지: - [1], [1], 1. 또는 1)
        if re.match(r"^[-•]?\s*\[?\d+[\].)]\s*", line):
            if current_ref:
                refs.append({
                    "paper_id": paper_id,
                    "ref_index": ref_index,
                    "title": current_ref.strip(),
                })
                ref_index += 1
            current_ref = re.sub(r"^[-•]?\s*\[?\d+[\].)]\s*", "", line)
        else:
            current_ref += " " + line

    if current_ref.strip():
        refs.append({
            "paper_id": paper_id,
            "ref_index": ref_index,
            "title": current_ref.strip(),
        })

    print(f"[ReferenceHunter:parse_references] {len(refs)}개 참고문헌 파싱 완료")
    return {"reference_links": refs}


# ── 서브그래프 빌드 ─────────────────────────────────────


def build_reference_graph():
    builder = StateGraph(ReferenceState)
    builder.add_node("parse_references", parse_references)
    builder.add_edge(START, "parse_references")
    builder.add_edge("parse_references", END)
    return builder.compile()


reference_graph = build_reference_graph()
