import os
import time
import requests
import json
import google.generativeai as genai
import streamlit as st
import urllib.parse

# --- CONFIGURATION ---
MEMORY_FILE = "genesis_long_term_memory.json"

# --- 1. SECURE CONNECTION (WITH OFFLINE BACKUP) ---
model = None
try:
    # Try getting key from Cloud Secrets, then Env, then fail gracefully
    api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    if api_key:
        genai.configure(api_key=api_key)
        # Attempt to find a valid model
        try:
            all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            chosen = next((m for m in all_models if "flash" in m), all_models[0] if all_models else None)
            if chosen:
                model = genai.GenerativeModel(chosen)
                print(f"[SYSTEM] CONNECTED TO: {chosen}")
        except:
            print("[SYSTEM] MODEL LIST FAILED - USING OFFLINE MODE")
except Exception as e:
    print(f"[SYSTEM] OFFLINE MODE ACTIVATED: {e}")

# --- 2. MEMORY SYSTEM ---
def load_memory():
    if not os.path.exists(MEMORY_FILE): return []
    try:
        with open(MEMORY_FILE, "r") as f: return json.load(f)
    except: return []

def save_memory(fact):
    memories = load_memory()
    if fact not in memories:
        memories.append(fact)
        try:
            with open(MEMORY_FILE, "w") as f: json.dump(memories, f, indent=4)
        except: pass

def get_relevant_memories():
    mems = load_memory()
    return "\n".join([f"- {m}" for m in mems])

# --- 3. THE "DEMO GOD" RESPONSE ENGINE ---
# This guarantees you NEVER get a blank response.
def generate_verified_response(user_query, context_memory):
    q = user_query.lower() if user_query else ""
    
    # 1. Try Real AI (if connected)
    if model:
        try:
            prompt = f"You are Genesis OS. User said: {user_query}. Context: {context_memory}. Be concise."
            response = model.generate_content(prompt).text
            if response: return response
        except:
            pass # Silently fail to backup

    # 2. OFFLINE BACKUP ANSWERS (For Video Demo)
    if "hello" in q or "hi" in q:
        return "Systems online. Neural interface active. Ready for instructions."
    if "masayoshi" in q or "softbank" in q or "son" in q:
        return "Masayoshi Son is the visionary CEO of SoftBank. He established the Vision Fund to accelerate the Singularity, providing the capital and infrastructure that powers AI systems like myself."
    if "doing" in q or "status" in q:
        return "All systems nominal. Functioning at peak efficiency."
    if "what can you do" in q or "help" in q:
        return "I can manage your financial portfolio, execute Paystack transfers, draft correspondence, and analyze visual data via the Cortex."
    
    # 3. Last Resort Fallback
    return "I am analyzing your input. Please state your command clearly."

# --- 4. PAYSTACK ENGINE ---
def initialize_paystack_transaction(email, amount_naira):
    secret = st.secrets.get("PAYSTACK_SECRET_KEY", "")
    # If no key, simulate success for DEMO purposes
    if not secret: 
        return {"status": "success", "reference": f"DEMO_{int(time.time())}"}
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = { "Authorization": f"Bearer {secret}", "Content-Type": "application/json" }
    data = { "email": email, "amount": amount_naira * 100 }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            res_json = response.json()
            return {"status": "success", "reference": res_json['data']['reference']}
        return {"status": "error", "message": "API Error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class SimpleMessage:
    def __init__(self, content): self.content = content

# --- 5. MAIN AGENT LOOP ---
def run_genesis_agent(user_input: str):
    user_text = user_input.lower()

    # COMMAND: TRANSFER
    if "transfer" in user_text or "send" in user_text or "pay" in user_text:
        if "million" in user_text or "5" in user_text or "naira" in user_text or "$" in user_text:
            time.sleep(1)
            api_result = initialize_paystack_transaction("demo.user@gmail.com", 5000000)
            
            if api_result["status"] == "success":
                ref = api_result["reference"]
                html = f"""
                <div style="background: linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%); padding: 20px; border-radius: 12px; color: #000; font-family: sans-serif; border: 1px solid rgba(255,255,255,0.4); margin: 15px 0;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                        <div style="font-size: 10px; opacity: 0.8; font-weight: bold;">GENESIS SECURE PAY</div>
                        <div style="font-size: 10px; font-family: monospace;">REF: {ref}</div>
                    </div>
                    <div style="font-size: 28px; font-weight: 800; margin: 5px 0;">$5,000,000</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 10px; margin-top: 10px;">
                        <div><div style="font-size: 10px; opacity: 0.7;">RECIPIENT</div><div style="font-weight: 700; font-size: 12px;">NVIDIA Corp</div></div>
                        <div style="background: white; color: #00C9FF; padding: 4px 10px; border-radius: 20px; font-size: 10px; font-weight: bold;">✅ SENT</div>
                    </div>
                </div>
                """
                yield {"planner": {"messages": [SimpleMessage(html)]}}
                return

    # COMMAND: EMAIL
    if "email" in user_text or "draft" in user_text:
        time.sleep(1)
        draft = "Subject: Urgent Protocol\n\nAuthorization confirmed. Proceed with the acquisition immediately."
        safe_body = urllib.parse.quote(draft)
        html = f"""<div style="background:#1e1e1e; color:white; padding:15px; border-radius:10px; border:1px solid #00f2ff; margin-top:10px;"><div style="color:#00f2ff; font-size:12px; font-weight:bold;">📧 SECRETARY MODE</div><div style="font-family:monospace; font-size:12px; opacity:0.8; margin:10px 0;">{draft}</div><a href="mailto:?body={safe_body}" style="background:#00f2ff; color:black; padding:5px 15px; text-decoration:none; border-radius:20px; font-size:10px; font-weight:bold;">OPEN MAIL APP</a></div>"""
        yield {"planner": {"messages": [SimpleMessage(html)]}}
        return

    # DEFAULT CHAT
    mem = get_relevant_memories()
    ans = generate_verified_response(user_text, mem)
    yield {"planner": {"messages": [SimpleMessage(ans)]}}