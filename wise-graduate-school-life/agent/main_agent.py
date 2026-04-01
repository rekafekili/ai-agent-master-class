from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from agent.state import PaperState
from agent.tools.pdf_parser import parse_paper
from agent.tools.vocabulary import extract_section_vocab, save_vocabulary


def route_sections(state: PaperState) -> list[Send]:
    """parse_paper 결과의 섹션들을 각각 extract_section_vocab 노드로 병렬 fan-out."""
    return [
        Send("extract_section_vocab", {
            "paper_id": state["paper_id"],
            "section": section,
        })
        for section in state["sections"]
    ]


graph_builder = StateGraph(PaperState)

graph_builder.add_node("parse_paper", parse_paper)
graph_builder.add_node("extract_section_vocab", extract_section_vocab)
graph_builder.add_node("save_vocabulary", save_vocabulary)

graph_builder.add_edge(START, "parse_paper")
graph_builder.add_conditional_edges("parse_paper", route_sections, ["extract_section_vocab"])
graph_builder.add_edge("extract_section_vocab", "save_vocabulary")
graph_builder.add_edge("save_vocabulary", END)

graph = graph_builder.compile()
