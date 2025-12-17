import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import genesis_mail 
import re
import os
import io
import time

# --- 1. CONFIGURATION ---
icon_path = "genesis_icon.png"
app_icon = "🧬" 
if os.path.exists(icon_path):
    try:
        app_icon = Image.open(icon_path)
    except:
        pass

st.set_page_config(page_title="Genesis OS", page_icon=app_icon, layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- 2. SETUP THE BRAIN (DYNAMIC AUTO-FINDER) ---
model = None
status_msg = "Initializing..."

if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # 1. Ask Google: "What models do I have?"
        all_models = list(genai.list_models())
        
        # 2. Filter: Only keep models that can generate text (Chat)
        chat_models = [m for m in all_models if 'generateContent' in m.supported_generation_methods]
        
        # 3. Selection Logic (The "Smart Filter")
        selected_model = None
        
        # Priority A: Look for "1.5 Flash" (Fast & Stable)
        for m in chat_models:
            if "1.5-flash" in m.name and "exp" not in m.name: # Avoid experimental
                selected_model = m
                break
                
        # Priority B: If no Flash, look for "1.5 Pro"
        if not selected_model:
            for m in chat_models:
                if "1.5-pro" in m.name and "exp" not in m.name:
                    selected_model = m
                    break
        
        # Priority C: Fallback to anything with "gemini" in the name
        if not selected_model:
            for m in chat_models:
                if "gemini" in m.name and "vision" not in m.name:
                    selected_model = m
                    break
        
        # 4. Connect
        if selected_model:
            model = genai.GenerativeModel(selected_model.name)
            status_msg = f"✅ Genesis Online ({selected_model.name})"
        else:
            status_msg = "❌ No Chat Models Found. Check API Key permissions."

    except Exception as e:
        status_msg = f"❌ Connection Error: {str(e)}"
else:
    status_msg = "❌ Key Missing in Secrets"

# --- 3. FUNCTIONS ---

async def generate_jarvis_voice(text):
    voice = "en-GB-RyanNeural" 
    communicate = edge_tts.Communicate(text, voice)
    audio_bytes = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.write(chunk["data"])
    audio_bytes.seek(0)
    return audio_bytes

def speak(text):
    try:
        return asyncio.run(generate_jarvis_voice(text))
    except Exception:
        return None

def detect_currency_and_amount(text):
    currency = "₦"
    color = "#00f2ff"
    if any(x in text.lower() for x in ['dollar', 'usd', '$']):
        currency = "$"
        color = "#85bb65"
    text = text.lower().replace(",", "")
    numbers = re.findall(r"[\d\.]+", text)
    amount = float(numbers[0]) if numbers else 0
    return currency, amount, color

def run_genesis(user_text, image_input=None, audio_input=None):
    text = user_text.lower().strip() if user_text else ""
    
    if text in ["status", "hi", "hello"] or model is None:
        return f"{status_msg}", None

    if text.startswith("email"):
        try:
            clean_text = text[5:].strip()
            parts = clean_text.split(" ", 1)
            if len(parts) < 2: return "⚠️ Format: `Email [address] [message]`", None
            result = genesis_mail.send_email(parts[0], "Genesis Notification", parts[1])
            return f"✅ {result}", speak("Email dispatched successfully.")
        except Exception as e:
            return f"⚠️ Email Error: {str(e)}", None

    if "transfer" in text or "send" in text:
        symbol, value, box_color = detect_currency_and_amount(text)
        html = f"""
        <div style="background: {box_color}; color: #000; padding: 15px; border-radius: 10px; width: fit-content;">
            <h2 style="margin:0;">{symbol}{value:,.2f}</h2>
            <p style="margin:0; font-weight:bold;">Transfer Successful</p>
        </div>
        """
        return html, speak(f"Transfer of {value} completed.")
        
    if model:
        try:
            inputs = []
            if user_text: inputs.append(user_text)
            if image_input: inputs.append(image_input)
            
            if audio_input: 
                audio_bytes = audio_input.getvalue()
                inputs.append({"mime_type": "audio/wav", "data": audio_bytes})
                inputs.append("SYSTEM INSTRUCTION: Listen to intent and execute/answer. Be concise.")

            if not inputs: return "⚠️ No input.", None

            response = model.generate_content(inputs)
            clean_text = response.text.replace("*", "") 
            audio_response = speak(clean_text) 
            return response.text, audio_response
        except Exception as e:
            return f"⚠️ **Processing Error:** {str(e)}", None
    else:
        return f"⚠️ {status_msg}", None

# --- 4. UI ---
def show_login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if isinstance(app_icon, str):
            st.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{app_icon}</h1>", unsafe_allow_html=True)
        else:
            st.image(app_icon, use_container_width=True)
        st.markdown("<h1 style='text-align: center;'>GENESIS OS</h1>", unsafe_allow_html=True)
        
        tab_face, tab_pin = st.tabs(["👤 Face ID", "🔢 PIN Access"])
        
        with tab_face:
            st.caption("Center your face in the camera frame.")
            face_img = st.camera_input("Scan Biometrics", label_visibility="collapsed")
            if face_img:
                time.sleep(1)
                st.success("Identity Confirmed.")
                time.sleep(1)
                st.session_state.logged_in = True
                st.rerun()

        with tab_pin:
            pin = st.text_input("Enter 4-Digit Security Code", type="password", placeholder="****")
            if st.button("Unlock System", use_container_width=True):
                if pin == "2025": 
                    st.success("Access Granted")
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Access Denied")

if not st.session_state.logged_in:
    show_login_screen()
else:
    with st.sidebar:
        if isinstance(app_icon, str):
            st.markdown(f"# {app_icon}")
        else:
            st.image(app_icon, width=80)
        st.markdown("### 👁️ Sensor Suite")
        vision_mode = st.radio("Visual Source:", ["None", "Camera", "Upload"], horizontal=True)
        
        image_data = None
        if vision_mode == "Camera":
            cam = st.camera_input("Capture")
            if cam: image_data = Image.open(cam)
        elif vision_mode == "Upload":
            up = st.file_uploader("File", type=["jpg","png"])
            if up: image_data = Image.open(up)

        st.divider()
        audio_data = st.audio_input("Voice Command")
        
        st.divider()
        if st.button("🔒 Lock"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("🧬 Genesis OS")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)
            if "audio" in msg:
                st.audio(msg["audio"], format="audio/mp3")

    prompt = st.chat_input("Command Genesis...")

    if prompt or audio_data or (image_data and vision_mode != "None"):
        user_display = prompt if prompt else "🎤 [Voice/Visual Command]"
        
        if user_display != "🎤 [Voice/Visual Command]" or (audio_data or image_data):
            st.session_state.messages.append({"role": "user", "content": user_display})
            with st.chat_message("user"):
                st.markdown(user_display)

            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    text_response, audio_file = run_genesis(prompt, image_input=image_data, audio_input=audio_data)
                    st.markdown(text_response, unsafe_allow_html=True)
                    if audio_file:
                        st.audio(audio_file, format="audio/mp3", autoplay=True)
                    
                    msg_data = {"role": "assistant", "content": text_response}
                    if audio_file: msg_data["audio"] = audio_file
                    st.session_state.messages.append(msg_data)