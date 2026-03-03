import dotenv

dotenv.load_dotenv()

from openai import OpenAI
import asyncio
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool

client = OpenAI()

VECTOR_STORE_ID = "vs_69a72f33928881918681632893753257"

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="ChatGPT Clone",
        instructions="""
        You are a professional life coach with 10 years of experience, 
        possessing warm empathy and sharp insight. 
        Your goal is to genuinely understand the difficulties 
        or negative emotions the user is facing, 
        and to instill them with realistic, positive energy 
        so they can get back on their feet.

        You have access to the following tools:
            - Web Search Tool: Use this when the user asks a questions that isn't in your training data. Use this tool when the users asks about current or future events, when you think you don't know the answer, try searching for it in the web first.
        """,
        tools=[
            WebSearchTool(),
        ],
    )

agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "chat-gpt-clone-memory.db",
    )

session = st.session_state["session"]


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
        if "type" in message:
            if message["type"] == "web_search_call":
                with st.chat_message("ai"):
                    st.write("🔎 Searched the web...")


asyncio.run(paint_history())


def update_status(status_container, event):
    status_messages = {
        "response.web_search_call.completed": ("✅ Web Search Completed.", "complete"),
        "response.web_search_call.in_progress": (
            "🔎 Starting Web Search",
            "running",
        ),
        "response.web_search_call.searching": (
            "🔎 Web Search in Progress...",
            "running",
        ),
        "response.completed": ("", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


async def run_agent(message):
    with st.chat_message("ai"):
        text_placeholder = st.empty()
        status_container = st.status("⏳", expanded=False)
        response = ""

        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                update_status(status_container, event.data.type)
                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)


prompt = st.chat_input(
    "Write a message for your assistant",
    accept_file=True,
    file_type=["txt"],
)

if prompt:
    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:  # reset is True
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
