import streamlit as st
import time
import json
import os

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="GENESIS OS",
    page_icon="🧿",
    layout="wide"
)

# --- 2. CSS STYLING (Mobile Friendly) ---
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    div[data-testid="stChatMessage"] { background-color: #111111; border: 1px solid #333; border-radius: 10px; }
    /* Fix input box sticking to bottom */
    .stChatInput { bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. IMPORTS CHECK ---
try:
    from kernel import run_genesis_agent
except ImportError:
    st.error("⚠️ CRITICAL ERROR: kernel.py not found. Please check GitHub.")
    st.stop()

# --- 4. SESSION STATE SETUP ---
if "history" not in st.session_state:
    st.session_state.history = []

# --- 5. HEADER & TOOLS (No Sidebar for Mobile Stability) ---
st.markdown("### 🧿 GENESIS OS")

# Expandable Camera Section (Visual Cortex)
with st.expander("👁️ OPEN VISUAL CORTEX (CAMERA)", expanded=False):
    cam = st.camera_input("Scan Environment")
    if cam:
        st.success("Image Acquired. Processing...")
        # Simulate processing for demo
        time.sleep(1)
        st.session_state.history.append({"role": "assistant", "content": "Visual data analyzed. Environment: Secure. Systems nominal."})

# --- 6. CHAT HISTORY DISPLAY ---
# Display previous messages
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        # Check if content is HTML (Green Card) or Text
        if "<div" in msg["content"]:
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.write(msg["content"])

# --- 7. INPUT HANDLING ---
# We use standard chat input for maximum compatibility
user_input = st.chat_input("Enter command sequence...")

if user_input:
    # 1. Show User Message Immediately
    st.session_state.history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # 2. Generate Assistant Response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Run the Kernel
            for event in run_genesis_agent(user_input):
                for val in event.values():
                    if "messages" in val:
                        full_response = val["messages"][-1].content
                        # Render update
                        if "<div" in full_response:
                            response_placeholder.markdown(full_response, unsafe_allow_html=True)
                        else:
                            response_placeholder.write(full_response)
            
            # FINAL CHECK: If response is still empty, force a message
            if not full_response:
                full_response = "System Error: Empty Response. (Offline Mode Active)"
                response_placeholder.error(full_response)
                
        except Exception as e:
            full_response = f"⚠️ SYSTEM FAILURE: {str(e)}"
            response_placeholder.error(full_response)
        
        # Save to history
        st.session_state.history.append({"role": "assistant", "content": full_response})