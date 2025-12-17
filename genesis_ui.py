import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS  # <--- The Voice Engine
import genesis_mail 
import re
import os
import io

# --- 1. CONFIGURATION & ICON ---
icon_path = "genesis_icon.png"
if os.path.exists(icon_path):
    app_icon = Image.open(icon_path)
else:
    app_icon = "🧬"

st.set_page_config(page_title="Genesis OS", page_icon=app_icon, layout="wide")

# --- 2. SETUP THE BRAIN ---
model = None
status_msg = "❌ Neural Interface Offline"

if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        available_model = "gemini-1.5-flash" 
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name and 'flash' in m.name:
                    available_model = m.name
                    break
        model = genai.GenerativeModel(available_model)
        status_msg = "✅ Genesis Voice Systems Online"
    except Exception as e:
        status_msg = f"❌ API Error: {str(e)}"
else:
    status_msg = "❌ Key Missing in Secrets"

# --- 3. INTELLIGENCE FUNCTIONS ---

def speak(text):
    """Converts text to audio bytes for Streamlit to play."""
    try:
        # Create MP3 in memory (no file saving needed)
        tts = gTTS(text=text, lang='en', tld='com.ng') # Nigerian accent English if available, else standard
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes
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
    
    # --- COMMAND: STATUS ---
    if text in ["status", "hi", "hello"]:
        return f"{status_msg}. Ready.", None

    # --- COMMAND: EMAIL ---
    if text.startswith("email"):
        try:
            clean_text = text[5:].strip()
            parts = clean_text.split(" ", 1)
            if len(parts) < 2: return "⚠️ Format: `Email [address] [message]`", None
            result = genesis_mail.send_email(parts[0], "Genesis Notification", parts[1])
            return f"✅ {result}", speak("Email dispatched successfully.")
        except Exception as e:
            return f"⚠️ Email Error: {str(e)}", None

    # --- COMMAND: TRANSFER ---
    if "transfer" in text or "send" in text:
        symbol, value, box_color = detect_currency_and_amount(text)
        response_html = f"""
        <div style="background: {box_color}; color: #000; padding: 15px; border-radius: 10px; width: fit-content;">
            <h2 style="margin:0;">{symbol}{value:,.2f}</h2>
            <p style="margin:0; font-weight:bold;">Transfer Successful</p>
        </div>
        """
        return response_html, speak(f"Transfer of {value} completed.")
        
    # --- COMMAND: AI BRAIN ---
    if model:
        try:
            inputs = []
            if user_text: inputs.append(user_text)
            if image_input: inputs.append(image_input)
            if audio_input: 
                audio_bytes = audio_input.getvalue()
                inputs.append({"mime_type": "audio/wav", "data": audio_bytes})
                if not user_text: inputs.append("Listen to this audio and respond.")

            if not inputs: return "⚠️ No input detected.", None

            response = model.generate_content(inputs)
            # Create audio for the AI response
            audio_response = speak(response.text.replace("*", "")) # Remove markdown for cleaner speech
            return response.text, audio_response
            
        except Exception as e:
            return f"⚠️ **Processing Error:** {str(e)}", None
    else:
        return "⚠️ System Offline.", None

# --- 4. THE UI LAYOUT ---

with st.sidebar:
    st.image(app_icon, width=80)
    st.markdown("### 👁️ Sensor Suite")
    
    st.markdown("**Visual Input**")
    vision_mode = st.radio("Source:", ["None", "Camera", "Upload"], horizontal=True, label_visibility="collapsed")
    
    image_data = None
    if vision_mode == "Camera":
        cam = st.camera_input("Capture")
        if cam: image_data = Image.open(cam)
    elif vision_mode == "Upload":
        up = st.file_uploader("File", type=["jpg","png"])
        if up: image_data = Image.open(up)

    st.divider()
    st.markdown("**Audio Input**")
    audio_data = st.audio_input("Record Voice Command")

st.title("🧬 Genesis OS")
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)
        # Re-display audio if it exists in history
        if "audio" in msg:
            st.audio(msg["audio"], format="audio/mp3")

prompt = st.chat_input("Command Genesis...")

if prompt or audio_data or (image_data and vision_mode != "None"):
    
    user_display = prompt if prompt else "🎤 [Audio/Visual Command Sent]"
    
    if user_display != "🎤 [Audio/Visual Command Sent]" or (audio_data or image_data):
        st.session_state.messages.append({"role": "user", "content": user_display})
        with st.chat_message("user"):
            st.markdown(user_display)

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                # Get both text AND audio back
                text_response, audio_file = run_genesis(prompt, image_input=image_data, audio_input=audio_data)
                
                st.markdown(text_response, unsafe_allow_html=True)
                
                # If audio was generated, play it
                if audio_file:
                    st.audio(audio_file, format="audio/mp3", autoplay=True)
                
                # Save to history
                msg_data = {"role": "assistant", "content": text_response}
                if audio_file:
                    msg_data["audio"] = audio_file
                st.session_state.messages.append(msg_data)