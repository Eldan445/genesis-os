import streamlit as st
import io
import base64
import json
from gtts import gTTS
from kernel import run_genesis_agent
from langchain_core.messages import HumanMessage, SystemMessage
from streamlit_mic_recorder import speech_to_text

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="GENESIS OS", page_icon="🧬", layout="wide", initial_sidebar_state="collapsed")

# --- 2. HOLOGRAPHIC CSS (THE NEW LOOK) ---
def inject_jarvis_style():
    st.markdown("""
    <style>
        /* MAIN BACKGROUND - Deep Blue Radial Gradient */
        .stApp {
            background: radial-gradient(circle at 50% 10%, #0f1c3f 0%, #020c1b 100%);
            color: #e6f1ff;
            font-family: 'Segoe UI', 'Roboto', sans-serif;
        }
        
        /* HIDE UI CLUTTER */
        #MainMenu, footer, header {visibility: hidden;}
        div[data-testid="stToolbar"] {display: none;}
        
        /* HOLOGRAPHIC CARDS (Glassmorphism) */
        .stChatMessage {
            background: rgba(17, 34, 64, 0.7);
            border: 1px solid rgba(100, 255, 218, 0.2);
            backdrop-filter: blur(12px);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        /* STATUS WIDGET */
        div[data-testid="stStatusWidget"] {
            background: rgba(16, 33, 62, 0.9);
            border: 1px solid #64ffda;
            color: #64ffda;
            border-radius: 8px;
        }

        /* THE ORB (Voice Button) - Updated to Blue/Cyan */
        div.stButton > button:first-child {
            width: 160px !important; 
            height: 160px !important; 
            border-radius: 50% !important;
            background: radial-gradient(circle, #00f2ff 0%, #0078ff 100%);
            border: 2px solid #ffffff !important;
            box-shadow: 0 0 30px #0078ff, inset 0 0 20px #ffffff;
            color: #ffffff !important;
            font-size: 18px !important; 
            font-weight: 600 !important;
            margin: 0 auto !important; 
            display: block !important;
            transition: all 0.3s ease;
        }
        
        div.stButton > button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 60px #00f2ff;
        }

        /* TYPOGRAPHY */
        h1, h2, h3 {
            color: #ccd6f6 !important;
            text-shadow: 0 0 10px rgba(0, 242, 255, 0.3);
        }
        p {
            color: #8892b0 !important;
            font-size: 1.1rem;
        }
        
        /* SIDEBAR STYLING */
        section[data-testid="stSidebar"] {
            background-color: #020c1b;
            border-right: 1px solid rgba(100, 255, 218, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. AUDIO SYSTEM ---
def text_to_speech_autoplay(text):
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        b64 = base64.b64encode(audio_fp.getvalue()).decode()
        md = f"""<audio autoplay style="display:none;"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""
        st.markdown(md, unsafe_allow_html=True)
    except: pass

def clean_response_text(content):
    if isinstance(content, list): return "".join([b.get('text', '') for b in content if isinstance(b, dict)])
    return str(content)

# --- 4. MAIN APP ---
def main():
    inject_jarvis_style()
    
    if "messages" not in st.session_state: st.session_state.messages = []

    # --- SIDEBAR: NEURAL LINK ---
    with st.sidebar:
        st.markdown("### 💠 **NEURAL LINK**")
        st.caption("Upload your `token.json` for private access.")
        uploaded_file = st.file_uploader("Authentication Token", type="json")
        if uploaded_file:
            st.session_state["user_custom_token"] = json.load(uploaded_file)
            st.success("✅ SYSTEM LINKED")
        if st.button("DISCONNECT"):
            if "user_custom_token" in st.session_state: del st.session_state["user_custom_token"]
            st.rerun()

    # --- HUD HEADER ---
    c1, c2 = st.columns([3, 1])
    with c1: 
        st.markdown("## 🧬 **GENESIS DASHBOARD**")
    with c2: 
        # Modern Toggle
        quiet_toggle = st.toggle("🔇 QUIET MODE", value=False)

    # --- CENTRAL ORB ---
    st.write("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        voice_text = speech_to_text(language='en', start_prompt="TAP TO ACTIVATE", stop_prompt="LISTENING...", just_once=True, use_container_width=True, key='jarvis_mic')

    # --- CHAT CONTAINER ---
    chat_container = st.container()
    text_input = st.chat_input("Enter command sequence...")

    # --- LOGIC ---
    user_prompt = None
    is_voice_mode = False

    if voice_text:
        user_prompt = voice_text
        is_voice_mode = True 
    elif text_input:
        user_prompt = text_input
        is_voice_mode = False 

    # --- EXECUTION ---
    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with chat_container:
            for message in st.session_state.messages:
                # Avatar Icons
                role_icon = "🤖" if message["role"] == "assistant" else "👤"
                with st.chat_message(message["role"]): 
                    st.markdown(f"**{role_icon}** {message['content']}")

        with st.status("💠 PROCESSING DATA STREAM...", expanded=True) as status:
            final_text = ""
            try:
                agent_stream = run_genesis_agent(user_prompt)
                for event in agent_stream:
                    for node_data in event.values():
                        if "messages" in node_data:
                            msg = node_data["messages"][-1]
                            if isinstance(msg, SystemMessage) and "permission" in str(msg.content).lower():
                                status.update(label="🔒 AWAITING AUTHORIZATION", state="running")
                            final_text += clean_response_text(msg.content)
            except Exception as e:
                final_text = f"SYSTEM ERROR: {str(e)}"
                status.update(label="❌ CONNECTION FAILED", state="error")
            status.update(label="✅ EXECUTION COMPLETE", state="complete", expanded=False)

        if final_text:
            st.session_state.messages.append({"role": "assistant", "content": final_text})
            with chat_container:
                with st.chat_message("assistant"): st.markdown(f"**🤖** {final_text}")
            
            # Mission Success Card
            if "booked" in final_text.lower() or "sent" in final_text.lower():
                st.balloons()
                st.info(f"**✅ TASK COMPLETED SUCCESSFULLY**\n\n> {final_text}")

            if is_voice_mode and not quiet_toggle:
                text_to_speech_autoplay(final_text)

if __name__ == "__main__":
    main()