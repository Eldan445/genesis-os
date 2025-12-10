# genesis_ui.py
import streamlit as st
import io
import json
from gtts import gTTS
from kernel import run_genesis_agent
from langchain_core.messages import HumanMessage, SystemMessage
from streamlit_mic_recorder import speech_to_text

# --- 1. CONFIGURATION (Mobile & Audio Setup) ---
st.set_page_config(page_title="Genesis AGI", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for Mobile "App-Like" Feel
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div.block-container {padding-top: 1rem; padding-bottom: 5rem;}
/* Style the mic button to be prominent */
div[data-testid="stMarkdownContainer"] p {font-size: 1.1rem;}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS ---

def text_to_speech_autoplay(text):
    """Converts text to audio and plays it automatically."""
    try:
        # Generate audio using Google TTS
        tts = gTTS(text=text, lang='en', slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        # Display audio player (hidden or visible)
        st.audio(audio_fp, format='audio/mp3', start_time=0)
    except Exception as e:
        # If audio fails (e.g., network), just log it silently or show a small toast
        pass

def clean_response_text(content):
    """Parses raw Gemini JSON/List output into clean text."""
    if isinstance(content, list):
        # Join text parts if it's a list of blocks
        return "".join([block.get('text', '') for block in content if isinstance(block, dict) and 'text' in block])
    return str(content)

# --- 3. SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. CHAT HISTORY DISPLAY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. VOICE INPUT HANDLER ---

# Create two columns: One for Mic, One for Text Fallback
col1, col2 = st.columns([1, 4])

with col1:
    st.write("🎙️")
    # This button activates the mic on your phone/laptop
    # It returns the transcribed text automatically
    voice_text = speech_to_text(language='en', use_container_width=True, just_once=True, key='mic')

with col2:
    text_input = st.chat_input("Or type command...")

# Determine which input to use (Voice takes priority if active)
user_prompt = voice_text if voice_text else text_input

if user_prompt:
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Agent Execution
    with st.status("🧠 Genesis Processing...", expanded=True) as status:
        
        agent_stream = run_genesis_agent(user_prompt)
        final_text_accumulator = ""
        is_paused = False
        
        for event in agent_stream:
            # LangGraph events are usually {'node_name': {'messages': [...]}}
            # We iterate over values to find the message data regardless of node name
            for node_data in event.values():
                if not isinstance(node_data, dict) or "messages" not in node_data:
                    continue
                
                msg = node_data["messages"][-1]
                
                # A. Handle Permission Gate (The Pause)
                if isinstance(msg, SystemMessage) and "Permission" in str(msg.content):
                    status.update(label="🔒 Awaiting Permission", state="running", expanded=True)
                    is_paused = True
                    
                    with st.chat_message("assistant"):
                        st.warning(msg.content) # Use warning for visibility
                        # We also speak the permission request!
                        text_to_speech_autoplay("I need permission to proceed.")
                        
                    st.session_state.messages.append({"role": "assistant", "content": msg.content})
                    # Break the inner loop to stop processing this stream
                    break 
                
                # B. Handle Tool Calls (Status Update Only)
                elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # Safe access to tool name
                    try:
                        tool_name = msg.tool_calls[0].get('name', 'Tool')
                    except AttributeError:
                        tool_name = msg.tool_calls[0].name
                        
                    app_name = tool_name.split(':')[0].replace('_', ' ').title()
                    status.update(label=f"🛠️ Accessing {app_name}...", state="running")
                
                # C. Handle Final Text (Accumulate Clean Text)
                else:
                    # Clean the raw JSON/UMB logs here!
                    clean_chunk = clean_response_text(msg.content)
                    final_text_accumulator += clean_chunk

            # Stop the outer loop if we paused for permission
            if is_paused:
                break
                
            # Handle Planner Status Updates if present at top level
            if "plan_status" in event.get('planner', {}):
                status.update(label=f"🧠 {event['planner']['plan_status']}...", state="running")

        # 3. Final Output & Audio
        if final_text_accumulator:
            # Display Text
            with st.chat_message("assistant"):
                st.markdown(final_text_accumulator)
            
            # Save to History
            st.session_state.messages.append({"role": "assistant", "content": final_text_accumulator})
            
            # Close Status Bar
            status.update(label="✅ Complete", state="complete", expanded=False)
            
            # SPEAK THE RESPONSE
            text_to_speech_autoplay(final_text_accumulator)

        elif not is_paused:
            # If no text but finished (rare), just close status
            status.update(label="✅ Done", state="complete", expanded=False)