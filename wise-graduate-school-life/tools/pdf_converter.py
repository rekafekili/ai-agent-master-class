"""marker-pdf 기반 PDF 변환 + 섹션 분리 + Figure/Table 추출 노드."""

import re
from pathlib import Path

from agent.db import (
    get_connection,
    init_db,
    insert_figures_tables,
    insert_paper,
    insert_sections,
    get_paper_by_file_path,
    get_sections,
    get_figures_tables,
)
from agent.state import PaperState

FIGURES_DIR = Path(__file__).parent.parent / "asset" / "figures"


# ── PDF → Markdown 변환 (marker-pdf) ────────────────────


def _parse_pdf_to_markdown(file_path: str) -> tuple[str, str, dict]:
    """marker-pdf로 PDF를 Markdown으로 변환. (title, markdown, images) 반환."""
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(file_path)
    markdown = rendered.markdown
    title = (
        rendered.metadata.get("title", "")
        if rendered.metadata
        else ""
    )
    # title이 비어있으면 markdown의 첫 번째 heading 사용
    if not title:
        match = re.search(r"^#{1,3}\s+(.+)$", markdown, re.MULTILINE)
        title = match.group(1).strip() if match else Path(file_path).stem

    images = rendered.images  # dict[str, PIL.Image]
    return title, markdown, images


# ── Figure/Table 추출 ────────────────────────────────────


def _extract_figures_from_images(images: dict, paper_id: str) -> list[dict]:
    """marker-pdf의 rendered.images에서 Figure 이미지를 저장."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for i, (name, pil_img) in enumerate(images.items()):
        fname = f"{paper_id}_fig_{i + 1}.png"
        save_path = str(FIGURES_DIR / fname)
        pil_img.save(save_path)
        items.append({
            "item_type": "figure",
            "label": f"Figure {i + 1}",
            "caption": name,
            "image_path": save_path,
            "table_markdown": None,
        })
    return items


# ── 섹션 분리 + 필터링 ──────────────────────────────────


_SKIP_SECTION_KEYWORDS = {"@", "university", "institute", "department", "college",
                          "school of", "permission to make", "copyright", "acm isbn",
                          "doi.org", "corresponding author"}
_SKIP_HEADING_PATTERNS = {"ccs concepts", "acmreference format", "acm reference format"}


def _is_preamble_section(heading: str, content: str) -> bool:
    """본문 시작 전 메타/저자 정보 섹션인지 판별."""
    heading_lower = heading.lower().strip().rstrip(":")
    if heading_lower in _SKIP_HEADING_PATTERNS:
        return True
    content_lower = content.lower()
    return any(kw in content_lower for kw in _SKIP_SECTION_KEYWORDS)


def _is_numbered_heading(heading: str) -> bool:
    """'1 Introduction', '2.1 Method' 같은 번호가 붙은 본문 heading인지."""
    return bool(re.match(r"^\d+[\.\s]", heading.strip()))


def _split_sections_from_markdown(markdown: str) -> tuple[list[dict], str]:
    """Markdown을 heading 기준으로 섹션 분리하고, References 섹션을 별도 추출.

    논문 초반 저자/기관 정보 섹션은 필터링.
    """
    pattern = r"^(#{1,3})\s+(.+)$"
    lines = markdown.split("\n")

    raw_sections = []
    current_heading = "Untitled"
    current_level = 1
    current_lines: list[str] = []
    references_raw = ""
    in_references = False

    for line in lines:
        match = re.match(pattern, line)
        if match:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    if in_references:
                        references_raw = content
                        in_references = False
                    else:
                        raw_sections.append({
                            "heading": current_heading,
                            "content": content,
                            "level": current_level,
                        })

            current_heading = match.group(2).strip()
            current_level = len(match.group(1))
            current_lines = []

            heading_lower = current_heading.lower()
            if heading_lower in ("references", "bibliography", "reference"):
                in_references = True
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            if in_references:
                references_raw = content
            else:
                raw_sections.append({
                    "heading": current_heading,
                    "content": content,
                    "level": current_level,
                })

    # 저자/기관/메타 섹션 필터링
    sections = []
    body_started = False
    for s in raw_sections:
        if _is_numbered_heading(s["heading"]):
            body_started = True

        if body_started:
            sections.append(s)
        elif s["heading"].lower().strip() == "abstract":
            sections.append(s)
        elif not _is_preamble_section(s["heading"], s["content"]):
            sections.append(s)

    for i, s in enumerate(sections):
        s["section_index"] = i
        s["figures"] = []

    return sections, references_raw


def _map_figures_to_sections(
    sections: list[dict], figures_tables: list[dict], markdown: str
) -> list[dict]:
    """Figure/Table을 Markdown 내 위치 기반으로 가장 가까운 섹션에 매핑."""
    lines = markdown.split("\n")

    section_starts = []
    heading_pattern = r"^(#{1,3})\s+(.+)$"
    heading_idx = 0
    ref_headings = {"references", "bibliography", "reference"}

    for line_no, line in enumerate(lines):
        match = re.match(heading_pattern, line)
        if match and match.group(2).strip().lower() not in ref_headings:
            section_starts.append((heading_idx, line_no))
            heading_idx += 1

    for item in figures_tables:
        search_text = item.get("caption", "") or item.get("label", "")
        if not search_text:
            continue

        search_snippet = search_text[:30]
        item_line = -1
        for line_no, line in enumerate(lines):
            if search_snippet in line:
                item_line = line_no
                break

        if item_line == -1:
            continue

        best_section_idx = 0
        for sec_idx, sec_start_line in section_starts:
            if sec_start_line <= item_line:
                best_section_idx = sec_idx
            else:
                break

        if best_section_idx < len(sections):
            item["section_index"] = best_section_idx
            sections[best_section_idx]["figures"].append(item)

    return figures_tables


# ── 메인 노드 ───────────────────────────────────────────


def convert_and_divide(state: PaperState) -> dict:
    """PDF를 marker-pdf로 변환하고, 섹션 분리 + Figure 추출하는 통합 노드."""
    print("[convert_and_divide] 노드 시작")
    file_path = state["file_path"]
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"PDF 파일만 지원합니다. 현재 파일: {path.suffix}")

    # DB 캐시 확인
    conn = get_connection()
    init_db(conn)
    existing = get_paper_by_file_path(conn, str(path))
    if existing:
        sections = get_sections(conn, existing["id"])
        figures_tables = get_figures_tables(conn, existing["id"])
        conn.close()
        print(f"[convert_and_divide] 캐시 히트 — {existing['title']} ({len(sections)}개 섹션)")
        return {
            "paper_id": existing["id"],
            "paper_title": existing["title"],
            "sections": sections,
            "references_raw": "",
            "figures_tables": figures_tables,
        }

    # marker-pdf 변환
    print("[convert_and_divide] marker-pdf 변환 시작...")
    title, markdown, images = _parse_pdf_to_markdown(str(path))
    print(f"[convert_and_divide] 변환 완료: {title}")

    # DB에 paper 저장
    paper_id = insert_paper(conn, title, str(path))

    # Figure 추출 (marker-pdf images)
    print("[convert_and_divide] Figure 추출 중...")
    figures_tables = _extract_figures_from_images(images, paper_id)
    print(f"[convert_and_divide] {len(figures_tables)}개 Figure 추출")

    # 섹션 분리
    sections, references_raw = _split_sections_from_markdown(markdown)
    print(f"[convert_and_divide] {len(sections)}개 섹션 분리, References {'있음' if references_raw else '없음'}")

    # Figure → 섹션 매핑
    figures_tables = _map_figures_to_sections(sections, figures_tables, markdown)

    # DB 저장
    insert_sections(conn, paper_id, sections)
    if figures_tables:
        insert_figures_tables(conn, paper_id, figures_tables)
    conn.close()

    print(f"[convert_and_divide] DB 저장 완료 (paper_id: {paper_id})")
    return {
        "paper_id": paper_id,
        "paper_title": title,
        "sections": sections,
        "references_raw": references_raw,
        "figures_tables": figures_tables,
    }
