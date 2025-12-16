import os
import streamlit as st
import google.generativeai as genai
import re

# --- CONFIGURATION ---
# 1. Load API Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    st.toast("✅ Key Loaded & Model Configured", icon="🔋")
except Exception as e:
    st.error(f"❌ SETUP ERROR: {str(e)}")
    model = None

class SimpleMessage:
    def __init__(self, content):
        self.content = content

def extract_amount(text):
    # Simple extraction logic
    text = text.lower().replace(",", "")
    numbers = re.findall(r"[\d\.]+", text)
    return float(numbers[0]) if numbers else 0

def run_genesis_agent(user_input: str):
    user_text = user_input.lower()
    
    # --- 1. HANDLE "HI" / "HELLO" MANUALLY ---
    if user_text in ["hi", "hello", "hey"]:
        yield {"planner": {"messages": [SimpleMessage("Systems online. Ready for instructions.")]}}
        return

    # --- 2. HANDLE TRANSFERS ---
    if "transfer" in user_text:
        amount = extract_amount(user_text)
        html = f"""
        <div style="background: #00f2ff; color: #000; padding: 15px; border-radius: 10px;">
            <b>₦{amount:,.2f}</b><br>SENT SUCCESSFULLY
        </div>
        """
        yield {"planner": {"messages": [SimpleMessage(html)]}}
        return

    # --- 3. THE "TRUTH TELLER" AI BLOCK ---
    if model:
        try:
            # Try to connect to Google
            response = model.generate_content(user_text)
            yield {"planner": {"messages": [SimpleMessage(response.text)]}}
        except Exception as e:
            # THIS IS THE FIX: PRINT THE ERROR
            error_msg = f"⚠️ CRITICAL ERROR: {str(e)}"
            yield {"planner": {"messages": [SimpleMessage(error_msg)]}}
    else:
        yield {"planner": {"messages": [SimpleMessage("⚠️ System Offline: Check API Key Secrets")]}}