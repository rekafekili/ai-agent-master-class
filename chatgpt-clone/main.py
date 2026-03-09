import streamlit as st

# print("ruinning") # UI에 변경사항이 발생하면, 모든 코드가 재실행됨.

# 코드가 재실행 되어도 유지될 수 있는 데이터 필요 -> `st.session_state`

if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

st.header("Hello!")

name = st.text_input("What is your name?")

if name:
    st.write(f"Hello {name}")
    st.session_state["is_admin"] = True

print(st.session_state["is_admin"])
