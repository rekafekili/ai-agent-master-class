import dotenv

dotenv.load_dotenv()

import streamlit as st
import asyncio
from openai import OpenAI
from agents import SQLiteSession, Runner, Agent, InputGuardrailTripwireTriggered
from multi_agents.triage_agent import triage_agent
from models import UserAccountContext


client = OpenAI()

user_account_context = UserAccountContext(
    name="은모래",
    favorites=["김밥", "불고기"],
    allergies=["땅콩"],
)

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history", "restaurant-chat-history.db"
    )

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent

session: SQLiteSession = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()
    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"])


asyncio.run(paint_history())


async def run_agent(message):
    with st.chat_message("ai"):
        text_placeholder = st.empty()
        response = ""

        st.session_state["text_placeholder"] = text_placeholder

        stream = Runner.run_streamed(
            st.session_state["agent"],
            message,
            session=session,
            context=user_account_context,
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


message = st.chat_input("Write a message for your assistant")

if message:
    if "text_placeholder" in st.session_state:
        st.session_state["text_placeholder"].empty()

    with st.chat_message("human"):
        st.write(message)

    asyncio.run(run_agent(message))

with st.sidebar:
    reset = st.button("Reset Memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
