from dotenv import load_dotenv

load_dotenv()

import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from agent.state import PaperState
from agent.tools.pdf_parser import parse_paper
from agent.tools.vocabulary import extract_vocabulary, human_review, save_vocabulary


graph_builder = StateGraph(PaperState)

graph_builder.add_node("parse_paper", parse_paper)
graph_builder.add_node("extract_vocabulary", extract_vocabulary)
graph_builder.add_node("human_review", human_review)
graph_builder.add_node("save_vocabulary", save_vocabulary)

graph_builder.add_edge(START, "parse_paper")
graph_builder.add_edge("parse_paper", "extract_vocabulary")
graph_builder.add_edge("extract_vocabulary", "human_review")
graph_builder.add_edge("save_vocabulary", END)

conn = sqlite3.connect("checkpointer.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

graph = graph_builder.compile(checkpointer=checkpointer)
