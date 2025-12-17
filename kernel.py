import streamlit as st
import google.generativeai as genai
import re
import genesis_mail  # <--- Connects to your Email Script

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Genesis OS", page_icon="🧬", layout="centered")

# --- 2. SETUP THE BRAIN ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        status_msg = "✅ Neural Interface Online"
    else:
        model = None
        status_msg = "❌ Key Missing in Secrets"
except Exception as e:
    model = None
    status_msg = f"❌ Connection Error: {str(e)}"

# --- 3. HELPER FUNCTIONS ---
def extract_amount(text):
    text = text.lower().replace(",", "")
    numbers = re.findall(r"[\d\.]+", text)
    return float(numbers[0]) if numbers else 0

def run_genesis(user_input):
    text = user_input.lower().strip()
    
    # --- COMMAND A: STATUS ---
    if text in ["status", "hi", "hello"]:
        return f"{status_msg}. Ready for commands."

    # --- COMMAND B: SEND EMAIL ---
    # Usage: "Email [address] [message]"
    if text.startswith("email"):
        try:
            # 1. Clean string: "email bob@gmail.com hi" -> "bob@gmail.com hi"
            clean_text = text[5:].strip() 
            
            # 2. Split: Address is first word, Body is the rest
            parts = clean_text.split(" ", 1)
            
            if len(parts) < 2:
                return "⚠️ **Format Error:** Use: `Email [address] [message]`"
            
            target_email = parts[0]
            email_body = parts[1]
            
            # 3. Execute via Tool
            result = genesis_mail.send_email(target_email, "Message from Genesis", email_body)
            
            return f"""
            <div style="background: #2E7D32; color: #fff; padding: 15px; border-radius: 10px;">
                {result}<br>
                <small><b>To:</b> {target_email}</small>
            </div>
            """
        except Exception as e:
            return f"⚠️ Email Error: {str(e)}"

    # --- COMMAND C: TRANSFER SIMULATION ---
    if "transfer" in text or "send" in text:
        amount = extract_amount(text)
        return f"""
        <div style="background: #00f2ff; color: #000; padding: 15px; border-radius: 10px; margin-top: 10px;">
            <h2 style="margin:0;">₦{amount:,.2f}</h2>
            <p style="margin:0;">Transfer Successful via Opay Bridge</p>
        </div>
        """
        
    # --- COMMAND D: AI BRAIN (THE TRUTH TELLER) ---
    if model:
        try:
            response = model.generate_content(user_input)
            return response.text
        except Exception as e:
            return f"⚠️ **GOOGLE ERROR:** {str(e)}"
    else:
        return "⚠️ System Offline. Please check API Key."

# --- 4. THE UI ---
st.title("🧬 Genesis OS")
st.caption(status_msg)

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "<div" in msg["content"]:
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# Input Logic
if prompt := st.chat_input("Command Genesis..."):
    # 1. Show User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate & Show Response
    with st.chat_message("assistant"):
        with st.spinner("Processing Protocol..."):
            response = run_genesis(prompt)
            
            if "<div" in response:
                st.markdown(response, unsafe_allow_html=True)
            else:
                st.markdown(response)
                
            st.session_state.messages.append({"role": "assistant", "content": response})