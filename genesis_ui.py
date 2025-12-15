import streamlit as st
import time
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="GENESIS OS", page_icon="🧿", layout="wide")

# --- 2. IMPORTS & SETUP ---
try:
    from kernel import run_genesis_agent, text_to_speech_autoplay
except ImportError:
    st.error("⚠️ CRITICAL: kernel.py is missing. Please check GitHub files.")
    st.stop()

# Mic Check
try:
    from streamlit_mic_recorder import speech_to_text
    mic_available = True
except ImportError:
    mic_available = False

# --- 3. SESSION STATE ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "history" not in st.session_state: st.session_state.history = []
if "last_processed" not in st.session_state: st.session_state.last_processed = ""
if "mic_key" not in st.session_state: st.session_state.mic_key = 0 

# --- 4. CSS (CYBERPUNK STYLE) ---
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #fff; }
    .stTextInput > div > div > input { background-color: #111; color: #fff; border: 1px solid #333; }
    .stButton > button { background-color: #00f2ff; color: #000; font-weight: bold; border-radius: 5px; width: 100%; }
    div[data-testid="stChatMessage"] { background-color: #111; border: 1px solid #333; }
    .stChatInput { bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 5. LOGIN SCREEN ---
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br><h1 style='text-align: center; color: #00f2ff;'>🧿 GENESIS OS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; opacity: 0.7; letter-spacing: 2px;'>SECURE NEURAL LINK</p>", unsafe_allow_html=True)
        
        password = st.text_input("ENTER ACCESS CODE", type="password")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("INITIALIZE LINK"):
                if password == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("⛔ ACCESS DENIED")
        with col_b:
            if st.button("REQUEST DEMO KEY"):
                with st.spinner("Authenticating..."): time.sleep(1.5)
                st.success("ACCESS GRANTED. CODE: 1234")
    st.stop()

# --- 6. MAIN INTERFACE ---
st.markdown("### 🧿 GENESIS OS: ACTIVE")

# Chat History
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        if "<div" in msg["content"]: st.markdown(msg["content"], unsafe_allow_html=True)
        else: st.write(msg["content"])

# --- 7. INPUT AREA (ANTI-LOOP MIC) ---
c1, c2 = st.columns([1, 8])

voice_val = None
with c1:
    if mic_available:
        dynamic_key = f"mic_{st.session_state.mic_key}"
        voice_text = speech_to_text(start_prompt="🎙️", stop_prompt="🛑", just_once=True, key=dynamic_key)
        
        if voice_text and voice_text != st.session_state.last_processed:
            voice_val = voice_text
            st.session_state.last_processed = voice_text
            st.session_state.mic_key += 1
    else:
        st.caption("No Mic")

with c2:
    text_val = st.chat_input("Enter command...")

final_input = voice_val if voice_val else text_val

if final_input:
    # 1. User Message
    st.session_state.history.append({"role": "user", "content": final_input})
    
    # 2. Assistant Response
    with st.chat_message("assistant"):
        place = st.empty()
        full_res = ""
        try:
            for event in run_genesis_agent(final_input):
                for val in event.values():
                    if "messages" in val:
                        full_res = val["messages"][-1].content
                        if "<div" in full_res: place.markdown(full_res, unsafe_allow_html=True)
                        else: place.write(full_res)
            
            # 3. VOICE REPLY
            audio_html = text_to_speech_autoplay(full_res)
            if audio_html: st.markdown(audio_html, unsafe_allow_html=True)
                
        except Exception as e:
            full_res = f"System Error: {e}"
            place.error(full_res)
            
        st.session_state.history.append({"role": "assistant", "content": full_res})
    
    time.sleep(0.5)
    st.rerun()