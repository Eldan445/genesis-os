import streamlit as st
import google.generativeai as genai
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Genesis Diagnostics", page_icon="🔧", layout="wide")

st.title("🔧 Genesis System Scan")
st.write("Checking available neural pathways...")

if "GOOGLE_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # Get the list
        all_models = list(genai.list_models())
        
        st.subheader("Your Available Models:")
        found_stable = False
        
        for m in all_models:
            # We only care about models that can generate content (Chat)
            if 'generateContent' in m.supported_generation_methods:
                st.code(f"{m.name}")
                
                # Check if we found the one we want
                if "1.5-flash" in m.name:
                    found_stable = True

        st.divider()
        
        if found_stable:
            st.success("✅ GOOD NEWS: Gemini 1.5 Flash IS available. We just need to target it correctly.")
        else:
            st.warning("⚠️ STRANGE: Gemini 1.5 Flash is NOT in your list. This explains the errors.")
            st.write("Please copy the list above and send it to me.")

    except Exception as e:
        st.error(f"❌ Connection Failed: {str(e)}")
else:
    st.error("❌ Key Missing in Secrets")