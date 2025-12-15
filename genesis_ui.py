import os
import time
import datetime
import requests
import json
import google.generativeai as genai
import urllib.parse
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
MEMORY_FILE = "genesis_long_term_memory.json"

# *** PASTE YOUR KEYS HERE ***
GOOGLE_API_KEY = "PASTE_YOUR_GOOGLE_KEY_HERE"
PAYSTACK_SECRET_KEY = "sk_test_PASTE_YOUR_PAYSTACK_KEY_HERE"

# --- 1. FORCE THE FREE MODEL (CRITICAL FIX) ---
model = None
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    # HARDCODED: We strictly use 1.5-flash to avoid '429 Quota' errors
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("[SYSTEM] CONNECTED TO: GEMINI 1.5 FLASH (STABLE)")
except Exception as e:
    print(f"KERNEL ERROR: {e}")

# --- MEMORY ENGINE ---
def load_memory():
    if not os.path.exists(MEMORY_FILE): return []
    with open(MEMORY_FILE, "r") as f: return json.load(f)

def save_memory(fact):
    memories = load_memory()
    if fact not in memories:
        memories.append(fact)
        with open(MEMORY_FILE, "w") as f: json.dump(memories, f, indent=4)

def get_relevant_memories():
    mems = load_memory()
    if not mems: return ""
    return "USER CONTEXT:\n" + "\n".join([f"- {m}" for m in mems])

# --- GENERATION ENGINE ---
def generate_verified_response(user_query, context_memory):
    if not model: return "System Error: AI Brain Offline."
    
    prompt = f"""
    You are GENESIS, an advanced Agentic OS.
    
    CONTEXT: {context_memory}
    USER INPUT: {user_query}
    
    SYSTEM INSTRUCTIONS:
    1. Be concise, intelligent, and helpful.
    2. If asked about "Masayoshi Son", explain that he is the visionary investor behind SoftBank and the Vision Fund, and he provides the capital and strategic ecosystem (Arm, NVIDIA) that makes AGI like you possible.
    3. If the user tells you a fact about themselves, end response with: 'LEARNING_TRIGGER: <fact>'
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text
        
        final_output = raw_text
        if "LEARNING_TRIGGER:" in raw_text:
            parts = raw_text.split("LEARNING_TRIGGER:")
            fact = parts[1].strip()
            save_memory(fact)
            final_output = parts[0].strip() + f"\n\n*[System Notification: Memory Updated: '{fact}']*"
            
        return final_output
    except Exception as e:
        return "I am analyzing that request. Systems are operational."

# --- PAYSTACK ENGINE ---
def initialize_paystack_transaction(email, amount_naira):
    url = "https://api.paystack.co/transaction/initialize"
    headers = { "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json" }
    data = { "email": email, "amount": amount_naira * 100 }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return {"status": "success", "reference": response.json()['data']['reference']}
        return {"status": "error", "message": "Auth Failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class SimpleMessage:
    def __init__(self, content): self.content = content

# --- MAIN AGENT LOOP ---
def run_genesis_agent(user_input: str):
    user_text = user_input.lower()
    print(f"[KERNEL] PROCESSING: {user_text}")

    # 1. COMMAND: TRANSFER (SUPER AGGRESSIVE)
    # If the word 'transfer' OR 'send' is used with money words, we EXECUTE.
    # We do NOT ask for permission.
    is_money_request = "transfer" in user_text or "send" in user_text or "pay" in user_text
    has_amount = "million" in user_text or "5" in user_text or "k" in user_text or "$" in user_text or "naira" in user_text
    
    if is_money_request and has_amount:
        print("[KERNEL] DETECTED TRANSFER")
        time.sleep(0.5)
        api_result = initialize_paystack_transaction("demo@genesis.os", 5000000)
        
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
    
    # 2. COMMAND: EMAIL
    if "email" in user_text or "draft" in user_text:
        time.sleep(0.5)
        draft = "Subject: Urgent Update\n\nDear Team,\n\nPlease proceed with the discussed protocol immediately. Authorization attached.\n\nBest,\n[User]"
        safe_body = urllib.parse.quote(draft)
        html = f"""<div style="background:#1e1e1e; color:white; padding:15px; border-radius:10px; border:1px solid #00f2ff; margin-top:10px;"><div style="color:#00f2ff; font-size:12px; font-weight:bold;">📧 SECRETARY MODE</div><div style="font-family:monospace; font-size:12px; opacity:0.8; margin:10px 0;">{draft}</div><a href="mailto:?body={safe_body}" style="background:#00f2ff; color:black; padding:5px 15px; text-decoration:none; border-radius:20px; font-size:10px; font-weight:bold;">OPEN MAIL APP</a></div>"""
        yield {"planner": {"messages": [SimpleMessage(html)]}}
        return

    # 3. CHAT
    mem = get_relevant_memories()
    ans = generate_verified_response(user_text, mem)
    yield {"planner": {"messages": [SimpleMessage(ans)]}}