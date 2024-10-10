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

# 쓰레드 제목 생성 함수
def generate_thread_title(question):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "사용자의 질문을 바탕으로 20자 내외의 간결한 제목 생성"},
            {"role": "user", "content": question}
        ],
        max_tokens=50
    )
    return response.choices[0].message.content.strip()

# 쓰레드 생성 함수
def create_thread(user_input):
    thread = client.beta.threads.create()
    title = generate_thread_title(user_input)
    st.session_state.threads.append({"id": thread.id, "title": title})
    st.session_state.thread_id = thread.id
    return thread

# 쓰레드 메시지 로드 함수
def load_thread_messages(thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    st.session_state.messages = [
        ChatMessage(role=msg.role, content=msg.content[0].text.value)
        for msg in reversed(messages.data)
    ]

# AI 응답 생성 함수
def get_ai_response(thread_id, run_id):
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            return messages.data[0].content[0].text.value
        elif run.status == 'failed':
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다."
        time.sleep(1)

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

# 사이드바에 쓰레드 목록 표시
with st.sidebar:
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

# 메인 콘텐츠
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