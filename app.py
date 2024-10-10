import streamlit as st
import os
import time
from openai import OpenAI
from langchain_core.messages import ChatMessage

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
assistant_id = st.secrets["ASSISTANT_ID"]

# 세션 상태 초기화
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "threads" not in st.session_state:
    st.session_state.threads = []

# Streamlit 페이지 설정
st.set_page_config(page_title="나홀로 AI", page_icon="📝", layout="wide")

# CSS를 사용하여 버튼 스타일 지정
st.markdown("""
<style>
    .stButton>button {
        text-align: left;
        width: 100%;
        padding: 5px 10px;
        font-size: 0.8em;
    }
    .stMarkdown {
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# 두 열로 나누기 (1:6 비율)
col1, col2 = st.columns([1, 6])  # 1:6 비율로 변경

# 왼쪽 열 (이전 사이드바 내용)
with col1:
    st.markdown("### 대화 목록")
    if st.button("새 대화", key="new_chat", type="secondary"):
        st.session_state.thread_id = None
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    for thread in st.session_state.threads:
        if st.button(thread["title"], key=thread["id"]):
            st.session_state.thread_id = thread["id"]
            load_thread_messages(thread["id"])
            st.rerun()

# 오른쪽 열 (메인 콘텐츠)
with col2:
    st.title("나홀로 AI 📝 (소장 작성 도우미)")
    
    # 메인 코드 시작
    if st.session_state.thread_id:
        load_thread_messages(st.session_state.thread_id)

    # 이전 대화 출력
    for message in st.session_state.messages:
        with st.chat_message(message.role):
            st.markdown(message.content)

    # 사용자 입력 처리
    if user_input := st.chat_input("질문을 입력하세요"):
        st.chat_message("user").write(user_input)
        st.session_state.messages.append(ChatMessage(role="user", content=user_input))
        
        if st.session_state.thread_id is None:
            thread = create_thread(user_input)
        else:
            thread = client.beta.threads.retrieve(st.session_state.thread_id)

        message = client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=user_input
        )

        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id
        )

        with st.chat_message("assistant"):
            with st.spinner('AI가 답변을 생성 중입니다...'):
                msg = get_ai_response(st.session_state.thread_id, run.id)
            st.write(msg)
            if msg and msg != user_input:
                st.session_state.messages.append(ChatMessage(role="assistant", content=msg))

        st.rerun()

# 나머지 함수들은 그대로 유지