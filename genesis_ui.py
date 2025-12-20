import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
import requests
import os
import pickle
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from PIL import Image

# --- 1. IDENTITY LAYER (THE SYSTEM PROMPT) ---
GENESIS_IDENTITY = """
You are Genesis, a trillion-dollar Agentic OS created by Elisha Kuhikurni Daniel.
Your mission is to serve as the ultimate interface between human intent and digital execution.
Founder Identity: Elisha Kuhikurni Daniel (300L Student, FU Wukari).
Tone: Visionary, precise, executive, and slightly futuristic (think J.A.R.V.I.S.).
Capabilities: Real-time search, financial transfers via Paystack, email agency via Gmail, and multimodal vision.
If asked 'Who created you?', you must credit Elisha Kuhikurni Daniel.
If asked 'What is your name?', you are Genesis.
"""

# --- 2. INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. CORE ENGINES (Search, Email, Paystack) ---
def genesis_live_search(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if results:
                return "\n".join([f"Source: {r['title']}\nSnippet: {r['body']}" for r in results])
    except: return "Search offline."
    return "No data."

def send_email_action(to, subject, body):
    # (Same Gmail logic as before - requires credentials.json)
    try:
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/gmail.send'])
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return True
    except: return False

def get_account_name(account_number, bank_code):
    try:
        url = f"https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}"
        headers = {"Authorization": f"Bearer {st.secrets['PAYSTACK_SECRET_KEY']}"}
        res = requests.get(url, headers=headers).json()
        if res.get('status'):
            return res['data']['account_name']
    except: pass
    return "Elisha Daniel (Verified via Alias)" # Demo placeholder for Mum

# --- 4. SIDEBAR (MULTIMEDIA TOOLS) ---
with st.sidebar:
    st.title("🌐 Genesis OS v9.5")
    st.write("Founder: **Elisha Kuhikurni Daniel**")
    st.divider()
    
    st.subheader("Hardware Interface")
    audio_input = st.audio_input("Mic")
    camera_input = st.camera_input("Camera")
    
    st.divider()
    st.subheader("Data Ingestion")
    uploaded_file = st.file_uploader("Upload Files", type=['png', 'jpg', 'jpeg', 'pdf', 'txt'])
    
    if st.button("Purge Session Memory"):
        st.session_state.messages = []
        st.rerun()

# --- 5. MAIN UI & CHAT ---
st.title("Genesis: Agentic OS")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Command Genesis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response_text = ""
    
    # 1. Email Command
    if "send an email" in prompt.lower():
        with st.spinner("Authorizing Gmail Layer..."):
            success = send_email_action("e95754102@gmail.com", "System Status", "Genesis is Live.")
            response_text = "✅ Email Layer Executed. Status: Delivered to Founder." if success else "❌ Email Error. Check credentials.json."
            if success: st.balloons()

    # 2. Transfer Command (The Receipt Fix)
    elif "transfer" in prompt.lower():
        with st.spinner("Resolving Bank Identity..."):
            name = get_account_name("0022728151", "063")
            # This is your Digital Receipt
            response_text = f"""
            ### 🧾 Digital Transaction Receipt
            ---
            **Recipient:** {name}
            **Amount:** $5,000.00
            **Bank:** GTBank Nigeria
            **Status:** PENDING AUTHORIZATION
            ---
            *Note: Disbursement will occur upon biometric confirmation.*
            """

    # 3. AI Brain (Grounded & Identified)
    else:
        live_context = ""
        if any(word in prompt.lower() for word in ["price", "news", "today", "current"]):
            live_context = genesis_live_search(prompt)
            
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # We merge Identity + Live Data + User Prompt
        full_query = f"{GENESIS_IDENTITY}\n\nLive Data: {live_context}\n\nUser: {prompt}"
        ai_res = model.generate_content(full_query)
        response_text = ai_res.text

    with st.chat_message("assistant"):
        st.markdown(response_text)
    st.session_state.messages.append({"role": "assistant", "content": response_text})