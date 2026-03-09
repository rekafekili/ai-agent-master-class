# https://docs.streamlit.io/
import streamlit as st
import time

st.write("Hello world!")

st.button("Click me please!")

st.text_input("Write your API KEY", max_chars=20)

st.feedback("faces")

with st.sidebar:
    st.badge("Badge 1")

tab1, tab2, tab3 = st.tabs(["Agents", "Chat", "Output"])

with tab1:
    st.header("Agent")
with tab2:
    st.header("Agent 2")
with tab3:
    st.header("Agent 3")

with st.chat_message("ai"):
    st.text("Hello!")
with st.chat_message("human"):
    st.text("Hi!")
with st.chat_message("user"):
    st.text("Hi, I'm User")
with st.chat_message("assistant"):
    st.text("Hi, I'm Assistant")
    with st.status("Agent is using tool") as status:
        time.sleep(1)
        status.update(label="Agent is searching the web....")
        time.sleep(2)
        status.update(label="Agent is reading the page....")
        time.sleep(3)
        status.update(label="Completed....")


st.chat_input(
    "Write a message for the assistant.",
    accept_file=True,
)
