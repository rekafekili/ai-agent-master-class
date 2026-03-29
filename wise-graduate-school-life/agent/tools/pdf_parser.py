import re
from pathlib import Path

from agent.db import (
    get_connection,
    init_db,
    insert_paper,
    insert_sections,
    get_paper_by_file_path,
    get_sections,
)
from agent.state import PaperState


def _parse_pdf_to_markdown(file_path: str) -> tuple[str, str]:
    """marker-pdf로 PDF를 Markdown으로 변환. (title, markdown) 반환."""
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(file_path)
    markdown = rendered.markdown
    title = (
        rendered.metadata.get("title", Path(file_path).stem)
        if rendered.metadata
        else Path(file_path).stem
    )
    return title, markdown


def _split_sections(markdown: str) -> list[dict]:
    """Markdown을 heading 기준으로 섹션 분리."""
    pattern = r"^(#{1,3})\s+(.+)$"
    lines = markdown.split("\n")

    sections = []
    current_heading = "Untitled"
    current_lines: list[str] = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append(
                        {
                            "heading": current_heading,
                            "content": content,
                        }
                    )
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(
                {
                    "heading": current_heading,
                    "content": content,
                }
            )

    for i, s in enumerate(sections):
        s["section_index"] = i

    return sections


def parse_paper(state: PaperState) -> PaperState:
    """PDF를 파싱하여 섹션으로 분리하고 DB에 저장하는 노드.
    이미 DB에 동일 file_path로 저장된 논문이 있으면 캐시된 결과를 반환."""
    print("[parse_paper] 노드 시작")
    file_path = state["file_path"]
    path = Path(file_path)
    print(f"[parse_paper] 파일 경로: {path}")

    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"PDF 파일만 지원합니다. 현재 파일: {path.suffix}")

    conn = get_connection()
    init_db(conn)

    existing = get_paper_by_file_path(conn, str(path))
    if existing:
        sections = get_sections(conn, existing["id"])
        conn.close()
        print(f"[parse_paper] 캐시 히트 — 기존 논문 사용: {existing['title']} ({len(sections)}개 섹션)")
        return {
            "paper_id": existing["id"],
            "paper_title": existing["title"],
            "sections": sections,
        }

    print("[parse_paper] marker-pdf 변환 시작...")
    title, markdown = _parse_pdf_to_markdown(str(path))
    print(f"[parse_paper] marker-pdf 변환 완료: {title}")

    sections = _split_sections(markdown)
    print(f"[parse_paper] 섹션 분리 완료: {len(sections)}개 섹션")

    if not sections:
        conn.close()
        raise ValueError("논문에서 섹션을 추출하지 못했습니다.")

    paper_id = insert_paper(conn, title, str(path))
    insert_sections(conn, paper_id, sections)
    conn.close()
    print(f"[parse_paper] DB 저장 완료 (paper_id: {paper_id})")

    return {
        "paper_id": paper_id,
        "paper_title": title,
        "sections": sections,
    }
