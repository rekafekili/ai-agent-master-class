import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "wise_grad.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    if conn is None:
        conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL REFERENCES papers(id),
            section_index INTEGER NOT NULL,
            heading TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL REFERENCES papers(id),
            section_index INTEGER,
            word TEXT NOT NULL,
            context_sentence TEXT,
            meaning_ko TEXT NOT NULL,
            meaning_en TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    return conn


def insert_paper(conn: sqlite3.Connection, title: str, file_path: str) -> str:
    paper_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO papers (id, title, file_path) VALUES (?, ?, ?)",
        (paper_id, title, file_path),
    )
    conn.commit()
    return paper_id


def insert_sections(
    conn: sqlite3.Connection, paper_id: str, sections: list[dict]
) -> None:
    conn.executemany(
        "INSERT INTO sections (paper_id, section_index, heading, content) VALUES (?, ?, ?, ?)",
        [
            (paper_id, s["section_index"], s["heading"], s["content"])
            for s in sections
        ],
    )
    conn.commit()


def get_paper(conn: sqlite3.Connection, paper_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    return dict(row) if row else None


def get_paper_by_file_path(conn: sqlite3.Connection, file_path: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM papers WHERE file_path = ?", (file_path,)
    ).fetchone()
    return dict(row) if row else None


def get_sections(conn: sqlite3.Connection, paper_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM sections WHERE paper_id = ? ORDER BY section_index",
        (paper_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_section(
    conn: sqlite3.Connection, paper_id: str, section_index: int
) -> dict | None:
    row = conn.execute(
        "SELECT * FROM sections WHERE paper_id = ? AND section_index = ?",
        (paper_id, section_index),
    ).fetchone()
    return dict(row) if row else None


def insert_vocabulary(
    conn: sqlite3.Connection, entries: list[dict]
) -> None:
    conn.executemany(
        "INSERT INTO vocabulary (paper_id, section_index, word, context_sentence, meaning_ko, meaning_en) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (e["paper_id"], e.get("section_index"), e["word"], e.get("context_sentence"), e["meaning_ko"], e.get("meaning_en"))
            for e in entries
        ],
    )
    conn.commit()


def get_vocabulary(conn: sqlite3.Connection, paper_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM vocabulary WHERE paper_id = ? ORDER BY section_index, id",
        (paper_id,),
    ).fetchall()
    return [dict(r) for r in rows]
