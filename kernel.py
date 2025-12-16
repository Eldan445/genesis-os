import os
import streamlit as st
import google.generativeai as genai
import re

# --- CONFIGURATION ---
try:
    # Try loading from secrets
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    model = None

class SimpleMessage:
    def __init__(self, content):
        self.content = content

def extract_amount(text):
    text = text.lower().replace(",", "")
    numbers = re.findall(r"[\d\.]+", text)
    return float(numbers[0]) if numbers else 0

def run_genesis_agent(user_input: str):
    user_text = user_input.lower()
    
    # 1. FIXED RESPONSES
    if user_text in ["hi", "hello", "hey"]:
        yield {"planner": {"messages": [SimpleMessage("Systems online. Ready.")]}}
        return

    # 2. TRANSFER COMMAND
    if "transfer" in user_text:
        amount = extract_amount(user_text)
        html = f"""
        <div style="background: #00f2ff; color: #000; padding: 15px; border-radius: 10px;">
            <b>₦{amount:,.2f}</b><br>SENT SUCCESSFULLY
        </div>
        """
        yield {"planner": {"messages": [SimpleMessage(html)]}}
        return

    # 3. AI RESPONSE (TRUTH TELLER)
    if model:
        try:
            response = model.generate_content(user_text)
            yield {"planner": {"messages": [SimpleMessage(response.text)]}}
        except Exception as e:
            # SHOW THE REAL ERROR
            yield {"planner": {"messages": [SimpleMessage(f"⚠️ CRITICAL API ERROR: {str(e)}")]}}
    else:
        yield {"planner": {"messages": [SimpleMessage("⚠️ OFFLINE: Key missing in Secrets")]}}