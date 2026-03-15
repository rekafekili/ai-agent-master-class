import os
import dotenv
from mocks import MENU_DATA, COMMON_ALLERGENS, AGENT_LIST

dotenv.load_dotenv()

import streamlit as st

# Streamlit Cloud: st.secrets에서 API 키 로드
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
import asyncio
from openai import OpenAI
from agents import (
    SQLiteSession,
    Runner,
    Agent,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
)
from multi_agents.triage_agent import triage_agent
from models import UserAccountContext


client = OpenAI()

if "user_context" not in st.session_state:
    st.title("🍽️  레스토랑에 오신 것을 환영합니다!")
    st.subheader("주문 전 간단한 정보를 입력해 주세요.")

    menu_names = [item["name"] for item in MENU_DATA]

    with st.form("user_info_form"):
        name = st.text_input("이름", placeholder="홍길동")
        favorites = st.multiselect("좋아하는 메뉴", options=menu_names)
        allergies = st.multiselect("알레르기", options=COMMON_ALLERGENS)
        submitted = st.form_submit_button("예약 시작하기")

    if submitted:
        if not name.strip():
            st.warning("이름을 입력해 주세요.")
        else:
            st.session_state["user_context"] = UserAccountContext(
                name=name.strip(),
                favorites=favorites,
                allergies=allergies,
            )
            st.rerun()
    st.stop()

ctx = st.session_state["user_context"]
session_id = f"chat-{ctx.name}"
if (
    "session" not in st.session_state
    or st.session_state.get("session_user") != ctx.name
):
    st.session_state["session"] = SQLiteSession(
        session_id, "restaurant-chat-history.db"
    )
    st.session_state["session_user"] = ctx.name

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent

session: SQLiteSession = st.session_state["session"]


def extract_assistant_text(message):
    """assistant 메시지에서 표시할 텍스트를 안전하게 추출"""
    content = message.get("content", "")

    # content가 문자열인 경우
    if isinstance(content, str):
        return content if content.strip() else None

    # content가 리스트인 경우
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                # output_text 타입
                if "text" in item:
                    texts.append(item["text"])
                # refusal 타입
                elif "refusal" in item:
                    texts.append(f"⚠️  {item['refusal']}")
        return "\n".join(texts) if texts else None

    return None


async def paint_history():
    messages = await session.get_items()
    for message in messages:
        if "role" not in message:
            continue

        role = message["role"]

        # 시스템 트리거 메시지 숨기기 (메인 채팅에서만)
        if role == "user" and str(message.get("content", "")).startswith("[시스템]"):
            continue

        with st.chat_message(role):
            if role == "user":
                st.write(message.get("content", ""))
            else:
                # assistant 메시지 텍스트 추출
                text = extract_assistant_text(message)
                if text:
                    st.write(text)


asyncio.run(paint_history())


async def run_agent(message):
    with st.chat_message("ai"):
        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        try:
            stream = Runner.run_streamed(
                st.session_state["agent"],
                message,
                session=session,
                context=st.session_state["user_context"],
            )

            async for event in stream.stream_events():
                if event.type == "raw_response_event":
                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response)
                elif event.type == "agent_updated_stream_event":
                    session_agent: Agent = st.session_state["agent"]
                    if session_agent.name != event.new_agent.name:
                        st.write(
                            f"🤖 Transfered from {session_agent.name} to {event.new_agent.name}"
                        )
                        st.session_state["agent"] = event.new_agent
                        text_placeholder = st.empty()
                        response = ""
        except InputGuardrailTripwireTriggered:
            st.write("죄송합니다. 답변 드릴 수 없습니다.")
            st.session_state["text_placeholder"].empty()
        except OutputGuardrailTripwireTriggered:
            st.write("죄송합니다. 답변 중 에러가 발생하였습니다.")
            st.session_state["text_placeholder"].empty()


# ── 첫 진입 시 에이전트 자동 인사 ──
if "greeted" not in st.session_state:
    st.session_state["greeted"] = True
    asyncio.run(run_agent("[시스템] 새로운 고객이 입장했습니다. 환영 인사를 해주세요."))

message = st.chat_input("Write a message for your assistant")

if message:
    if "text_placeholder" in st.session_state:
        st.session_state["text_placeholder"].empty()

    with st.chat_message("human"):
        st.write(message)

    asyncio.run(run_agent(message))

with st.sidebar:
    # ── 사용자 정보 ──
    ctx = st.session_state["user_context"]
    st.markdown(f"### 👤 {ctx.name}")
    st.caption(f"❤️  {', '.join(ctx.favorites) if ctx.favorites else '없음'}")
    st.caption(f"⚠️  {', '.join(ctx.allergies) if ctx.allergies else '없음'}")

    if st.button("정보 수정"):
        del st.session_state["user_context"]
        st.rerun()
    st.divider()

    # ── 에이전트 목록 (현재 활성 에이전트 강조) ──
    st.markdown("### 🤖 에이전트")
    current_agent_name = st.session_state["agent"].name

    for agent_info in AGENT_LIST:
        if agent_info["name"] == current_agent_name:
            # 활성 에이전트: 테두리 강조
            st.markdown(
                f"""<div style="border: 2px solid #FF6B6B; border-radius: 8px; 
                padding: 8px; margin: 4px 0;">                                                                                                     
                {agent_info['emoji']} <b>{agent_info['desc']}</b> ← 현재
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"  {agent_info['emoji']} {agent_info['desc']}")
    st.divider()

    # ── 채팅 내역 (간결 + 에이전트 그룹) ──
    st.markdown("### 💬 채팅 내역")
    messages = asyncio.run(session.get_items())

    for item in messages:
        if "role" not in item:
            continue

        # 메시지 표시 (간결하게)
        if item["role"] == "user":
            content = item.get("content", "")
            st.markdown(f"🙋 {content[:50]}{'...' if len(str(content)) > 50 else ''}")
        elif item.get("type") == "message":
            content = item.get("content", [{}])
            text = (
                content[0].get("text", "")
                if isinstance(content, list)
                else str(content)
            )
            st.markdown(f"🤖 {text[:50]}{'...' if len(text) > 50 else ''}")

    st.divider()

    reset = st.button("Reset Memory")
    if reset:
        asyncio.run(session.clear_session())
        for key in ["user_context", "agent", "greeted", "session", "session_user"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
