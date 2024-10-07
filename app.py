import streamlit as st
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit Secrets에서 API 키와 Assistant ID를 가져옵니다.
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
assistant_id = st.secrets["ASSISTANT_ID"]

# 함수들 정의
def create_thread():
    return client.beta.threads.create()

def add_message_to_thread(thread_id, content):
    return client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=content
    )

def run_assistant(thread_id, assistant_id):
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions="Please provide a response."
    )
    return run.id

def wait_for_run_completion(thread_id, run_id):
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run_status.status == 'completed':
            return
        elif run_status.status == 'failed':
            raise Exception("Assistant run failed")
        time.sleep(1)

def get_assistant_response(thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data[0].content[0].text.value

# Streamlit 앱
st.title("AI 소장 작성 도우미")

# 세션 상태 초기화
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = create_thread().id

if 'conversation' not in st.session_state:
    st.session_state.conversation = []

if 'run_id' not in st.session_state:
    st.session_state.run_id = None

if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

if 'process_message' not in st.session_state:
    st.session_state.process_message = False

# 대화 기록 표시
for i, message in enumerate(st.session_state.conversation):
    st.text(f"사용자: {message['user']}")
    st.text(f"AI: {message['ai']}")
    st.text("---")

# 메시지 처리 및 AI 응답 생성 함수
def process_message(user_input):
    if user_input.strip():
        if st.session_state.run_id:
            wait_for_run_completion(st.session_state.thread_id, st.session_state.run_id)
        
        add_message_to_thread(st.session_state.thread_id, user_input)
        
        run_id = run_assistant(st.session_state.thread_id, assistant_id)
        st.session_state.run_id = run_id
        wait_for_run_completion(st.session_state.thread_id, run_id)
        ai_response = get_assistant_response(st.session_state.thread_id)
        
        st.session_state.conversation.append({
            "user": user_input,
            "ai": ai_response
        })

# 사용자 입력 처리
def on_input_change():
    if st.session_state.user_input_field.strip():  # 입력이 비어있지 않은 경우에만 처리
        st.session_state.process_message = True
        st.session_state.user_input = st.session_state.user_input_field
        st.session_state.user_input_field = ""  # 입력 필드 초기화

user_input = st.text_input("메시지를 입력하세요:", key="user_input_field", on_change=on_input_change)

if st.session_state.process_message:
    process_message(st.session_state.user_input)
    st.session_state.process_message = False
    st.rerun()

# 소장 생성 버튼
if st.button("소장 생성", key="generate_complaint_button"):
    with st.spinner("소장을 작성 중입니다..."):
        add_message_to_thread(st.session_state.thread_id, "지금까지의 정보를 바탕으로 소장을 작성해주세요.")
        run_id = run_assistant(st.session_state.thread_id, assistant_id)
        wait_for_run_completion(st.session_state.thread_id, run_id)
        complaint = get_assistant_response(st.session_state.thread_id)
        st.session_state.complaint = complaint
    st.session_state.user_input = ""
    st.rerun()

# 생성된 소장 표시
if 'complaint' in st.session_state:
    st.write("생성된 소장:")
    st.write(st.session_state.complaint)

# 새로운 소장 작성 버튼
if st.button("새로운 소장 작성", key="new_complaint_button"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()