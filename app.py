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

# CSS를 사용하여 버튼 스타일 지정 및 사이드바 너비 조정
st.markdown("""
<style>
    .stButton>button {
        text-align: left;
        width: 100%;
    }
    .css-1d391kg {
        width: 50% !important;
    }
    .css-1a1fzpi {
        width: 50% !important;
    }
    section[data-testid="stSidebar"] {
        width: 50% !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 50% !important;
    }
</style>
""", unsafe_allow_html=True)

# 메인 콘텐츠 영역
st.title("나홀로 AI 📝 (소장 작성 도우미)")

# 쓰레드 제목 생성 함수
def generate_thread_title(question):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "사용자의 질문을 바탕으로 20자 내외의 간결한 제목 생성"},
            {"role": "user", "content": question}
        ],
        max_tokens=50  # 토큰 수를 늘려 더 긴 제목 생성
    )
    return response.choices[0].message.content.strip()

# 쓰레드 생성 함수
def create_thread(question):
    thread = client.beta.threads.create()
    title = generate_thread_title(question)
    st.session_state.threads.append({"id": thread.id, "title": title})
    st.session_state.thread_id = thread.id
    st.session_state.messages = []  # 메시지 초기화
    return thread

# 스트리밍 응답을 처리하는 함수
def get_ai_response(thread_id, run_id, timeout=60):
    start_time = time.time()
    
    while True:
        if time.time() - start_time > timeout:
            return "응답 생성 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            if messages.data:
                for content in messages.data[0].content:
                    if content.type == 'text':
                        return content.text.value
            break
        elif run.status == "failed":
            return "응답 생성에 실패했습니다. 다시 질문해 주시거나, 잠시 후 재시도해 주세요."
        
        time.sleep(1)  # 1초마다 상태 확인
    
    return "응답을 받지 못했습니다. 다시 시도해 주세요."

# 쓰레드 메시지 로드 함수
def load_thread_messages(thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    st.session_state.messages = []
    for msg in reversed(messages.data):
        role = "assistant" if msg.role == "assistant" else "user"
        content = msg.content[0].text.value if msg.content else ""
        st.session_state.messages.append(ChatMessage(role=role, content=content))

# 사이드바에 쓰레드 목록 표시
with st.sidebar:
    # 제목과 새 대화 버튼을 같은 줄에 배치
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### 대화 목록")
    with col2:
        if st.button("새 대화", key="new_chat", type="secondary"):
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()
    
    # 구분선 추가
    st.markdown("---")
    
    # 쓰레드 목록 (전체 너비 사용)
    for thread in st.session_state.threads:
        if st.button(thread["title"], key=thread["id"]):
            st.session_state.thread_id = thread["id"]
            load_thread_messages(thread["id"])
            st.rerun()

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
        if msg and msg != user_input:  # 사용자 입력과 다른 경우에만 메시지 추가
            st.session_state.messages.append(ChatMessage(role="assistant", content=msg))

    st.rerun()