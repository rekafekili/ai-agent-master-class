from dotenv import load_dotenv

load_dotenv()

import os
import re

import streamlit as st

from agent.db import (
    get_connection,
    init_db,
    get_sections,
    get_summaries,
    get_vocabulary,
    get_reference_links,
)
from agent.main_agent import graph

st.set_page_config(page_title="슬기로운 대학원 생활", page_icon="📚", layout="wide")

# ── session state 초기화 ──
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0
if "result" not in st.session_state:
    st.session_state.result = {}
if "current_section" not in st.session_state:
    st.session_state.current_section = 0


def save_uploaded_pdf(uploaded_file) -> str:
    os.makedirs("asset", exist_ok=True)
    save_path = os.path.join("asset", uploaded_file.name)
    if not os.path.exists(save_path):
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    return save_path


def reset_analysis():
    st.session_state.analysis_done = False
    st.session_state.result = {}
    st.session_state.upload_key += 1
    st.session_state.current_section = 0


# ═══════════════════════════════════════════════════════
# 결과 페이지 — 본문 + 우측 패널 (요약/단어장)
# ═══════════════════════════════════════════════════════

if st.session_state.analysis_done:
    res = st.session_state.result
    sections = res["sections"]
    total = len(sections)
    has_refs = bool(res["references"])
    total_pages = total + (1 if has_refs else 0)
    idx = st.session_state.current_section or 0

    # ── 상단: 논문 제목 + 네비게이션 ──
    st.markdown(
        f"<h2 style='text-align: center; margin-bottom: 0;'>{res['paper_title']}</h2>",
        unsafe_allow_html=True,
    )

    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 2, 2, 1])

    with nav_col1:
        if st.button("◀ 이전", use_container_width=True, disabled=(idx <= 0)):
            st.session_state.current_section -= 1
            st.rerun()
    with nav_col2:
        if st.button("▶ 다음", use_container_width=True, disabled=(idx >= total_pages - 1)):
            st.session_state.current_section += 1
            st.rerun()
    with nav_col3:
        if idx < total:
            st.markdown(
                f"<p style='text-align: center; line-height: 2.4;'>"
                f"섹션 <b>{idx + 1}</b> / {total}</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<p style='text-align: center; line-height: 2.4;'>"
                "<b>📑 참고문헌</b></p>",
                unsafe_allow_html=True,
            )
    with nav_col4:
        opts = [f"[{i}] {s['heading'][:35]}" for i, s in enumerate(sections)]
        if has_refs:
            opts.append("📑 참고문헌")
        selected = st.selectbox(
            "섹션 이동", range(len(opts)), index=idx,
            format_func=lambda i: opts[i], label_visibility="collapsed",
        )
        if selected != idx:
            st.session_state.current_section = selected
            st.rerun()
    with nav_col5:
        if st.button("📄 새 논문", use_container_width=True):
            reset_analysis()
            st.rerun()

    st.divider()

    # ── 참고문헌 페이지 ──
    if idx >= total:
        st.subheader("🔗 참고문헌")
        if res["references"]:
            for r in res["references"]:
                st.markdown(f"**[{r['ref_index'] + 1}]** {r['title']}")
        else:
            st.info("참고문헌 섹션을 찾지 못했습니다.")

    # ── 섹션 카드 페이지: 본문 + 우측 패널 ──
    else:
        section = sections[idx]
        section_index = section["section_index"]

        # 해당 섹션 데이터 조회
        section_vocab = [
            v for v in res["vocabulary"] if v.get("section_index") == section_index
        ]
        section_summary = next(
            (s for s in res["summaries"] if s.get("section_index") == section_index),
            None,
        )

        # 본문(좌) + 패널(우) 2분할
        col_body, col_panel = st.columns([3, 2])

        # ── 좌측: 본문 (스크롤 없이 전체 표시) ──
        with col_body:
            st.subheader(section["heading"])
            st.markdown(section["content"])

        # ── 우측: 요약 + 단어장 패널 ──
        with col_panel:
            # 요약 영역
            st.markdown("#### 📋 요약")
            if section_summary:
                st.markdown(section_summary["section_summary"])
                if section_summary.get("keywords"):
                    kw_text = " ".join(f"`{k}`" for k in section_summary["keywords"])
                    st.markdown(f"**키워드:** {kw_text}")
                if section_summary.get("paragraph_summaries"):
                    with st.expander(
                        f"문단별 요약 ({len(section_summary['paragraph_summaries'])}개)",
                    ):
                        for i, ps in enumerate(section_summary["paragraph_summaries"]):
                            st.markdown(f"**문단 {i + 1}**")
                            st.markdown(f"- EN: {ps['en']}")
                            st.markdown(f"- KO: {ps['ko']}")
            else:
                st.caption("이 섹션의 요약이 없습니다.")

            st.divider()

            # 단어장 영역
            st.markdown(f"#### 📝 단어장 ({len(section_vocab)}개)")
            if section_vocab:
                for v in section_vocab:
                    idiom_tag = " `관용구`" if v.get("is_idiom") else ""
                    with st.expander(
                        f"**{v['word']}**{idiom_tag} — {v['meaning_ko']}",
                    ):
                        st.markdown(f"**영어 정의:** {v['meaning_en']}")
                        st.caption(f"📖 {v['context_sentence']}")
            else:
                st.caption("이 섹션에서 추출된 단어가 없습니다.")


# ═══════════════════════════════════════════════════════
# 업로드 페이지 — 파일 업로드 + 진행 상황
# ═══════════════════════════════════════════════════════

else:
    st.title("📚 슬기로운 대학원 생활")
    st.markdown(
        "영어 논문을 업로드하면 **단어장**, **섹션 요약**, **참고문헌 목록**을 자동으로 생성합니다."
    )

    uploader_placeholder = st.empty()
    uploaded_file = uploader_placeholder.file_uploader(
        "PDF 업로드",
        type=["pdf"],
        label_visibility="collapsed",
        key=f"uploader_{st.session_state.upload_key}",
    )

    if uploaded_file:
        uploader_placeholder.empty()
        file_path = save_uploaded_pdf(uploaded_file)

        paper_title = ""
        total_sections = 0
        completed_vocab = 0
        completed_summaries = 0
        all_sections = []
        all_figures_tables = []
        all_vocabulary = []
        all_summaries = []
        all_references = []

        st.divider()
        title_display = st.empty()
        title_display.markdown(
            f"<h3 style='text-align: center;'>⏳ {uploaded_file.name} 분석 중...</h3>",
            unsafe_allow_html=True,
        )
        parse_header = st.empty()
        parse_header.caption("논문 파싱 중...")

        prog_col1, prog_col2, prog_col3 = st.columns(3)

        with prog_col1:
            st.markdown("#### 📝 VocaManager")
            st.caption("섹션/문단 별 영단어를 추출하고, 단어장으로 정리합니다.")
            vocab_header = st.empty()
            vocab_header.caption("대기 중...")
            vocab_log = st.container()
        with prog_col2:
            st.markdown("#### 📋 TutorAgent")
            st.caption("섹션/문단 별 요약 및 번역을 진행합니다.")
            tutor_header = st.empty()
            tutor_header.caption("대기 중...")
            tutor_log = st.container()
        with prog_col3:
            st.markdown("#### 🔗 ReferenceHunter")
            st.caption("참고 문헌 목록을 관리합니다.")
            refs_header = st.empty()
            refs_header.caption("대기 중...")
            refs_log = st.container()

        for event in graph.stream({"file_path": file_path}, stream_mode="updates"):
            if "convert_and_divide" in event:
                data = event["convert_and_divide"]
                paper_title = data.get("paper_title", "")
                all_sections = data.get("sections", [])
                all_figures_tables = data.get("figures_tables", [])
                total_sections = len(all_sections)
                fig_count = len(all_figures_tables)
                has_refs = bool(data.get("references_raw"))
                title_display.markdown(
                    f"<h3 style='text-align: center;'>{paper_title}</h3>",
                    unsafe_allow_html=True,
                )
                parse_header.caption(
                    f"✅ 파싱 완료 — {total_sections}개 섹션, {fig_count}개 Figure/Table"
                    f"{', 참고문헌 발견' if has_refs else ''}"
                )
                vocab_header.caption("작업 중...")
                tutor_header.caption("작업 중...")
                if has_refs:
                    refs_header.caption("작업 중...")

            elif "run_voca_manager" in event:
                new_words = event["run_voca_manager"].get("vocabulary", [])
                all_vocabulary.extend(new_words)
                completed_vocab += 1
                vocab_header.caption(f"진행 중 ({completed_vocab}/{total_sections})")
                vocab_log.write(f"✅ 섹션 {completed_vocab} — +{len(new_words)}개 단어")
                if completed_vocab >= total_sections:
                    vocab_header.caption(f"✅ 완료 — 총 {len(all_vocabulary)}개")

            elif "run_tutor_agent" in event:
                new_summaries = event["run_tutor_agent"].get("summaries", [])
                all_summaries.extend(new_summaries)
                completed_summaries += 1
                heading = new_summaries[0]["heading"] if new_summaries else "?"
                tutor_header.caption(f"진행 중 ({completed_summaries}/{total_sections})")
                tutor_log.write(f"✅ '{heading}' 완료")
                if completed_summaries >= total_sections:
                    tutor_header.caption(f"✅ 완료 — 총 {len(all_summaries)}개 섹션")

            elif "run_reference_hunter" in event:
                new_refs = event["run_reference_hunter"].get("reference_links", [])
                all_references.extend(new_refs)
                refs_header.caption(f"✅ 완료 — {len(new_refs)}개 참고문헌")
                for r in new_refs:
                    refs_log.write(f"[{r['ref_index'] + 1}] {r['title'][:80]}")

            elif "save_results" in event:
                pass

        st.session_state.result = {
            "paper_title": paper_title,
            "sections": all_sections,
            "figures_tables": all_figures_tables,
            "vocabulary": all_vocabulary,
            "summaries": all_summaries,
            "references": all_references,
        }
        st.session_state.current_section = 0
        st.session_state.analysis_done = True
        st.rerun()

    # ── 이전에 분석한 논문 목록 ──
    conn = get_connection()
    init_db(conn)
    papers = conn.execute(
        "SELECT id, title, created_at FROM papers ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    if papers:
        st.divider()
        st.markdown("#### 이전에 분석한 논문")
        for paper in papers:
            paper_id = paper["id"]
            paper_title = paper["title"]
            created = paper["created_at"][:10] if paper["created_at"] else ""
            col_title, col_btn = st.columns([5, 1])
            with col_title:
                st.markdown(f"📄 **{paper_title}** &nbsp; `{created}`")
            with col_btn:
                if st.button("보기", key=f"view_{paper_id}", use_container_width=True):
                    db_conn = get_connection()
                    init_db(db_conn)
                    st.session_state.result = {
                        "paper_title": paper_title,
                        "sections": get_sections(db_conn, paper_id),
                        "figures_tables": [],
                        "vocabulary": get_vocabulary(db_conn, paper_id),
                        "summaries": get_summaries(db_conn, paper_id),
                        "references": get_reference_links(db_conn, paper_id),
                    }
                    db_conn.close()
                    st.session_state.current_section = 0
                    st.session_state.analysis_done = True
                    st.rerun()
