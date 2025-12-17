import streamlit as st
import google.generativeai as genai
from PIL import Image
import genesis_mail 
import re

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Genesis OS", page_icon="🧬", layout="wide")

# --- 2. SETUP THE BRAIN ---
model = None
vision_model = None
status_msg = "❌ Neural Interface Offline"

if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # We need a model that supports vision (Gemini 1.5 Flash is best for this)
        model = genai.GenerativeModel('gemini-1.5-flash')
        status_msg = "✅ Genesis Vision Systems Online"
    except Exception as e:
        status_msg = f"❌ API Error: {str(e)}"
else:
    status_msg = "❌ Key Missing in Secrets"

# --- 3. HELPER FUNCTIONS ---
def extract_amount(text):
    text = text.lower().replace(",", "")
    numbers = re.findall(r"[\d\.]+", text)
    return float(numbers[0]) if numbers else 0

def run_genesis(user_input, image_input=None):
    text = user_input.lower().strip()
    
    # --- COMMAND: STATUS ---
    if text in ["status", "hi", "hello"]:
        return f"{status_msg}. Ready."

    # --- COMMAND: EMAIL ---
    if text.startswith("email"):
        try:
            clean_text = text[5:].strip()
            parts = clean_text.split(" ", 1)
            if len(parts) < 2: return "⚠️ Format: `Email [address] [message]`"
            result = genesis_mail.send_email(parts[0], "Genesis Update", parts[1])
            return f"✅ {result}"
        except Exception as e:
            return f"⚠️ Email Error: {str(e)}"

    # --- COMMAND: TRANSFER ---
    if "transfer" in text or "send" in text:
        amount = extract_amount(text)
        return f"""
        <div style="background: #00f2ff; color: #000; padding: 15px; border-radius: 10px;">
            <h2 style="margin:0;">₦{amount:,.2f}</h2>
            <p style="margin:0;">Transfer Successful</p>
        </div>
        """
        
    # --- COMMAND: AI BRAIN (TEXT + VISION) ---
    if model:
        try:
            if image_input:
                # If we have an image, we send [Text, Image]
                response = model.generate_content([user_input, image_input])
            else:
                # Text only
                response = model.generate_content(user_input)
            return response.text
        except Exception as e:
            return f"⚠️ **ANALYSIS ERROR:** {str(e)}"
    else:
        return "⚠️ System Offline."

# --- 4. THE UI LAYOUT ---
st.title("🧬 Genesis OS")
st.caption(status_msg)

# --- SIDEBAR: SENSOR SUITE (Camera & Uploads) ---
with st.sidebar:
    st.header("👁️ Sensor Suite")
    
    # Tab selection for input type
    input_type = st.radio("Input Source:", ["None", "Camera", "Upload File"])
    
    image_data = None
    
    if input_type == "Camera":
        cam_pic = st.camera_input("Activate Visual Sensor")
        if cam_pic:
            image_data = Image.open(cam_pic)
            st.success("Image Captured")
            
    elif input_type == "Upload File":
        up_file = st.file_uploader("Upload Document/Image", type=["jpg", "png", "jpeg", "webp"])
        if up_file:
            image_data = Image.open(up_file)
            st.image(image_data, caption="Ready for Analysis", use_column_width=True)

# --- CHAT INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# --- INPUT HANDLING ---
if prompt := st.chat_input("Command Genesis..."):
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Process with AI (Passing the image if it exists)
    with st.chat_message("assistant"):
        with st.spinner("Analyzing Data Stream..."):
            response = run_genesis(prompt, image_input=image_data)
            st.markdown(response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": response})