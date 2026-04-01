from dotenv import load_dotenv

load_dotenv()

import os

import streamlit as st

from agent.main_agent import graph

st.set_page_config(page_title="슬기로운 대학원 생활", page_icon="📚")
st.title("📚 슬기로운 대학원 생활")

# ── session state 초기화 ──
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 논문 PDF를 업로드해주세요. 📄\n\n영어 논문에서 핵심 단어를 추출하여 단어장을 만들어 드립니다.",
        }
    ]
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

# ── 채팅 히스토리 렌더링 ──
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def save_uploaded_pdf(uploaded_file) -> str:
    """업로드된 PDF를 asset/ 디렉토리에 저장하고 경로 반환."""
    os.makedirs("asset", exist_ok=True)
    save_path = os.path.join("asset", uploaded_file.name)
    if not os.path.exists(save_path):
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    return save_path


# ── PDF 업로드 ──
uploaded_file = st.file_uploader(
    "PDF 업로드", type=["pdf"], label_visibility="collapsed",
    key=f"uploader_{st.session_state.upload_key}",
)

if uploaded_file:
    # 사용자 메시지
    user_msg = f"📄 **{uploaded_file.name}** 업로드"
    st.session_state.messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    # 파일 저장 & 그래프 스트리밍 실행
    with st.chat_message("assistant"):
        file_path = save_uploaded_pdf(uploaded_file)

        paper_title = ""
        total_sections = 0
        completed_sections = 0
        all_vocabulary = []

        status = st.status("논문 분석 중...", expanded=True)
        progress_text = st.empty()

        for event in graph.stream({"file_path": file_path}, stream_mode="updates"):
            if "parse_paper" in event:
                data = event["parse_paper"]
                paper_title = data.get("paper_title", "")
                total_sections = len(data.get("sections", []))
                status.update(label=f"📄 {paper_title} — 단어 추출 중 (0/{total_sections})")
                progress_text.markdown(f"**{paper_title}** 파싱 완료 — {total_sections}개 섹션 발견")

            elif "extract_section_vocab" in event:
                new_words = event["extract_section_vocab"].get("vocabulary", [])
                all_vocabulary.extend(new_words)
                completed_sections += 1

                section_name = new_words[0]["section_index"] if new_words else "?"
                status.update(
                    label=f"📄 단어 추출 중 ({completed_sections}/{total_sections})"
                )
                status.write(
                    f"✅ 섹션 {section_name} 완료 — {len(new_words)}개 단어"
                )

            elif "save_vocabulary" in event:
                status.update(label="💾 단어장 저장 완료!", state="complete", expanded=False)

        progress_text.empty()

        # 최종 결과 메시지
        result_lines = [
            f"**{paper_title}** 분석 완료!",
            f"- 섹션: {total_sections}개",
            f"- 추출 및 저장된 단어: {len(all_vocabulary)}개",
            "",
            "**단어 프리뷰** (상위 20개):",
        ]
        for v in all_vocabulary[:20]:
            result_lines.append(f"- **{v['word']}** — {v['meaning_ko']}")

        if len(all_vocabulary) > 20:
            result_lines.append(f"- ... 외 {len(all_vocabulary) - 20}개")

        result_content = "\n".join(result_lines)
        st.markdown(result_content)

    st.session_state.messages.append({"role": "assistant", "content": result_content})
    st.session_state.upload_key += 1
    st.rerun()
