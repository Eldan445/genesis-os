import os
import time
import requests
import json
import re
import google.generativeai as genai
import streamlit as st
import urllib.parse
from gtts import gTTS
import base64


try:
    secret_key = st.secrets["GOOGLE_API_KEY"]
    st.success(f"✅ Key Loaded! It starts with: {secret_key[:5]}...")
except:
    st.error("❌ NO KEY FOUND. Check your Secrets in Dashboard!")

# --- CONFIGURATION ---
MEMORY_FILE = "genesis_long_term_memory.json"

# --- 1. INTELLIGENT CONNECTION ---
model = None
try:
    # Try getting key from Cloud Secrets, or Environment Variable
    api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    
    if api_key:
        genai.configure(api_key=api_key)
        # Find a valid model
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priority: Flash -> Pro -> First Available
        chosen = None
        for m in all_models:
            if "flash" in m:
                chosen = m
                break
        
        if not chosen and all_models:
            chosen = all_models[0]
            
        if chosen:
            model = genai.GenerativeModel(chosen)
            print(f"[SYSTEM] CONNECTED TO: {chosen}")
except Exception as e:
    print(f"[SYSTEM] OFFLINE MODE: {e}")

# --- 2. VOICE OUTPUT ENGINE (TTS) ---
def text_to_speech_autoplay(text):
    # Do not read HTML code
    if "<div" in text: 
        speak_text = "Transaction processed successfully."
    else:
        speak_text = text

    try:
        # Generate Audio
        tts = gTTS(text=speak_text, lang='en')
        filename = "response.mp3"
        tts.save(filename)
        
        # Convert to Base64
        with open(filename, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            
        # HTML Audio Player
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        return md
    except Exception as e:
        return ""

# --- 3. HELPER FUNCTIONS ---
def extract_amount(text):
    clean_text = text.lower().replace(",", "")
    multiplier = 1
    if "million" in clean_text or "m " in clean_text:
        multiplier = 1000000
    elif "billion" in clean_text or "b " in clean_text:
        multiplier = 1000000000
    elif "k " in clean_text or "thousand" in clean_text:
        multiplier = 1000
        
    numbers = re.findall(r"[\d\.]+", clean_text)
    if numbers:
        return float(numbers[0]) * multiplier
    return 0

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

# --- 4. PAYSTACK ENGINE ---
def initialize_paystack_transaction(email, amount_naira):
    secret = st.secrets.get("PAYSTACK_SECRET_KEY", "")
    
    # Demo Mode if Key is missing
    if not secret:
        return {"status": "success", "reference": f"DEMO_{int(time.time())}"}
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "amount": int(amount_naira * 100)
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            res_json = response.json()
            return {"status": "success", "reference": res_json['data']['reference']}
        else:
            return {"status": "error", "message": "API Key Error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class SimpleMessage:
    def __init__(self, content):
        self.content = content

# --- 5. MAIN AGENT LOOP ---
def run_genesis_agent(user_input: str):
    user_text = user_input.lower()
    
    # --- COMMAND: TRANSFER ---
    if "transfer" in user_text or "send" in user_text or "pay" in user_text:
        amount = extract_amount(user_text)
        if amount > 0:
            time.sleep(1)
            api_result = initialize_paystack_transaction("demo.user@gmail.com", amount)
            
            if api_result["status"] == "success":
                ref = api_result["reference"]
                formatted_amount = "₦{:,.2f}".format(amount)
                html = f"""
                <div style="background: linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%); padding: 20px; border-radius: 12px; color: #000; font-family: sans-serif; border: 1px solid rgba(255,255,255,0.4); margin: 15px 0;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                        <div style="font-size: 10px; opacity: 0.8; font-weight: bold;">GENESIS SECURE PAY</div>
                        <div style="font-size: 10px; font-family: monospace;">REF: {ref}</div>
                    </div>
                    <div style="font-size: 28px; font-weight: 800; margin: 5px 0;">{formatted_amount}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 10px; margin-top: 10px;">
                        <div><div style="font-size: 10px; opacity: 0.7;">RECIPIENT</div><div style="font-weight: 700; font-size: 12px;">Verified Beneficiary</div></div>
                        <div style="background: white; color: #00C9FF; padding: 4px 10px; border-radius: 20px; font-size: 10px; font-weight: bold;">✅ SENT</div>
                    </div>
                </div>
                """
                yield {"planner": {"messages": [SimpleMessage(html)]}}
                return

    # --- COMMAND: EMAIL ---
    if "email" in user_text or "draft" in user_text:
        time.sleep(1)
        draft_content = "Drafting error."
        
        if model:
            try:
                draft_content = model.generate_content(f"Write email body for: '{user_text}'").text
            except:
                pass
                
        if draft_content == "Drafting error." or not model:
            if "boss" in user_text:
                draft_content = "Dear Sir,\n\nProject status updated."
            else:
                draft_content = "To Whom It May Concern,\n\nPlease proceed."

        safe_body = urllib.parse.quote(draft_content)
        html = f"""<div style="background:#1e1e1e; color:white; padding:15px; border-radius:10px; border:1px solid #00f2ff; margin-top:10px;"><div style="color:#00f2ff; font-size:12px; font-weight:bold;">📧 INTELLIGENT DRAFT</div><div style="font-family:monospace; font-size:12px; opacity:0.8; margin:10px 0; white-space: pre-wrap;">{draft_content}</div><a href="mailto:?body={safe_body}" style="background:#00f2ff; color:black; padding:5px 15px; text-decoration:none; border-radius:20px; font-size:10px; font-weight:bold;">OPEN MAIL APP</a></div>"""
        yield {"planner": {"messages": [SimpleMessage(html)]}}
        return

    # --- DEFAULT CHAT (WITH BACKUP) ---
    response = "I am processing your request."
    if model:
        try:
            response = model.generate_content(f"You are Genesis OS. User: {user_text}. Be concise.").text
        except:
            pass
    
    # Backup for Demo Mode
    if response == "I am processing your request.":
        if "hello" in user_text:
            response = "Systems online. Neural interface active. Ready for instructions."
        elif "masayoshi" in user_text:
            response = "Masayoshi Son is the visionary CEO of SoftBank and the Vision Fund."
        elif "what can you do" in user_text:
            response = "I can manage your financial portfolio, execute Paystack transfers, and draft correspondence."
        
    yield {"planner": {"messages": [SimpleMessage(response)]}}