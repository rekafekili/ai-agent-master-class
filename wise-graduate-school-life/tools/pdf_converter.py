"""Docling 기반 PDF 변환 + 섹션 분리 + Figure/Table 추출 노드."""

import os
import re
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc.document import (
    DoclingDocument,
    PictureItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.labels import DocItemLabel

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


def _extract_title(doc: DoclingDocument) -> str:
    """문서에서 제목을 추출. TITLE 또는 첫 번째 section_header 사용."""
    for item, _level in doc.iterate_items():
        if isinstance(item, TextItem) and item.label in (
            DocItemLabel.TITLE,
            DocItemLabel.SECTION_HEADER,
        ):
            return item.text.strip()
    return doc.name or "Untitled"


def _crop_figure_from_pdf(pdf_path: str, page_no: int, bbox, paper_id: str, fig_count: int) -> str | None:
    """pypdfium2로 PDF 페이지를 렌더링 후 bbox 영역을 크롭하여 이미지로 저장."""
    try:
        import pypdfium2 as pdfium
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

        pdf = pdfium.PdfDocument(pdf_path)
        page = pdf[page_no - 1]  # 0-indexed
        scale = 2
        bitmap = page.render(scale=scale)
        pil_page = bitmap.to_pil()

        _w, h = pil_page.size
        # BOTTOMLEFT → PIL top-left 좌표 변환
        left = int(bbox.l * scale)
        top = int(h - bbox.t * scale)
        right = int(bbox.r * scale)
        bottom = int(h - bbox.b * scale)

        cropped = pil_page.crop((left, top, right, bottom))
        fname = f"{paper_id}_fig_{fig_count}.png"
        save_path = str(FIGURES_DIR / fname)
        cropped.save(save_path)
        pdf.close()
        return save_path
    except Exception:
        return None


def _extract_figures_and_tables(
    doc: DoclingDocument, paper_id: str, pdf_path: str
) -> list[dict]:
    """Docling iterate_items로 Figure/Table을 구조화 추출.

    이미지는 pypdfium2로 PDF에서 직접 크롭하여 저장.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    fig_count = 0
    tbl_count = 0

    for item, _level in doc.iterate_items():
        if isinstance(item, PictureItem):
            fig_count += 1
            label = f"Figure {fig_count}"
            caption = ""
            if item.captions:
                caption_texts = []
                for cap_ref in item.captions:
                    resolved = cap_ref.resolve(doc=doc)
                    if resolved and hasattr(resolved, "text"):
                        caption_texts.append(resolved.text)
                caption = " ".join(caption_texts)

            # pypdfium2로 bbox 크롭
            image_path = None
            if item.prov:
                prov = item.prov[0]
                image_path = _crop_figure_from_pdf(
                    pdf_path, prov.page_no, prov.bbox, paper_id, fig_count
                )

            items.append({
                "item_type": "figure",
                "label": label,
                "caption": caption,
                "image_path": image_path,
                "table_markdown": None,
            })

        elif isinstance(item, TableItem):
            tbl_count += 1
            label = f"Table {tbl_count}"
            caption = ""
            if hasattr(item, "captions") and item.captions:
                caption_texts = []
                for cap_ref in item.captions:
                    resolved = cap_ref.resolve(doc=doc)
                    if resolved and hasattr(resolved, "text"):
                        caption_texts.append(resolved.text)
                caption = " ".join(caption_texts)

            table_md = item.export_to_markdown(doc=doc)

            items.append({
                "item_type": "table",
                "label": label,
                "caption": caption,
                "image_path": None,
                "table_markdown": table_md,
            })

    return items


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
            # 이전 섹션 저장
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

            # References 섹션 감지
            heading_lower = current_heading.lower()
            if heading_lower in ("references", "bibliography", "reference"):
                in_references = True
        else:
            current_lines.append(line)

    # 마지막 섹션 처리
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
    # 본문 시작 = 첫 번째 번호 heading (예: "1 INTRODUCTION")
    # 그 전의 섹션 중 Abstract만 유지하고 나머지 메타 섹션은 제거
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

    # 각 섹션의 시작 라인 번호 찾기
    section_starts = []
    heading_pattern = r"^(#{1,3})\s+(.+)$"
    heading_idx = 0
    ref_headings = {"references", "bibliography", "reference"}

    for line_no, line in enumerate(lines):
        match = re.match(heading_pattern, line)
        if match and match.group(2).strip().lower() not in ref_headings:
            section_starts.append((heading_idx, line_no))
            heading_idx += 1

    # 각 figure/table의 위치를 markdown에서 찾아서 섹션에 매핑
    for item in figures_tables:
        search_text = item.get("caption", "") or item.get("label", "")
        if not search_text:
            continue

        # 캡션 텍스트의 처음 30자로 위치 탐색
        search_snippet = search_text[:30]
        item_line = -1
        for line_no, line in enumerate(lines):
            if search_snippet in line:
                item_line = line_no
                break

        if item_line == -1:
            continue

        # 가장 가까운 이전 섹션에 매핑
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


def convert_and_divide(state: PaperState) -> dict:
    """PDF를 Docling으로 변환하고, 섹션 분리 + Figure/Table 추출하는 통합 노드."""
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

    # Docling 변환
    print("[convert_and_divide] Docling 변환 시작...")
    converter = DocumentConverter()
    result = converter.convert(str(path))
    doc = result.document
    print("[convert_and_divide] Docling 변환 완료")

    # 제목 추출
    title = _extract_title(doc)
    print(f"[convert_and_divide] 제목: {title}")

    # DB에 paper 저장
    paper_id = insert_paper(conn, title, str(path))

    # Figure/Table 추출
    print("[convert_and_divide] Figure/Table 추출 중...")
    figures_tables = _extract_figures_and_tables(doc, paper_id, str(path))
    print(f"[convert_and_divide] {len(figures_tables)}개 Figure/Table 추출")

    # Markdown export → 섹션 분리
    markdown = doc.export_to_markdown()
    # HTML 코멘트를 보이는 텍스트로 변환
    markdown = markdown.replace("<!-- image -->", "> *[Figure]*\n")
    markdown = re.sub(
        r"<!-- 🖼️❌.*?-->",
        "> *[Figure]*\n",
        markdown,
    )
    markdown = markdown.replace(
        "<!-- formula-not-decoded -->",
        "*[수식]*",
    )
    sections, references_raw = _split_sections_from_markdown(markdown)
    print(f"[convert_and_divide] {len(sections)}개 섹션 분리, References {'있음' if references_raw else '없음'}")

    # Figure/Table → 섹션 매핑
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
