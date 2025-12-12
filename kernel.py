import streamlit as st
import os
import json
import uuid
import datetime
from typing import TypedDict, Sequence
from dotenv import load_dotenv

# LangChain / Groq
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.tools import DuckDuckGoSearchRun

# Google Tools
from langchain_google_community import GmailToolkit, CalendarToolkit

# Memory Import
from umb import get_memory_bus 

# --- 1. CONFIGURATION ---
load_dotenv()

def get_api_key():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            key = st.secrets["GROQ_API_KEY"]
        except:
            pass
    return key

# --- 2. TOOL LOADER ---
search_engine = DuckDuckGoSearchRun()

@tool
def research_tool(query: str):
    """Search the web for news, stocks, or facts."""
    return search_engine.run(query)

def get_genesis_tools():
    tools = [research_tool]
    gmail_api = None 
    calendar_api = None
    
    # SETUP AUTH
    auth_file = None
    if "user_custom_token" in st.session_state:
        try:
            auth_file = f"user_token_{uuid.uuid4()}.json"
            with open(auth_file, "w") as f: json.dump(st.session_state["user_custom_token"], f)
        except: pass
    elif os.path.exists("token.json"):
        auth_file = "token.json"
    elif "google_auth" in st.secrets:
        try:
            auth_file = "token.json"
            token_data = json.loads(st.secrets["google_auth"]["token_json"])
            with open(auth_file, "w") as f: json.dump(token_data, f)
        except: pass

    # LOAD RESOURCES
    if auth_file:
        try:
            g_toolkit = GmailToolkit(token_file=auth_file)
            gmail_api = g_toolkit.api_resource
            c_toolkit = CalendarToolkit(token_file=auth_file)
            calendar_api = c_toolkit.api_resource
            if "user_token_" in auth_file: os.remove(auth_file)
        except Exception as e: print(f"⚠️ TOOL ERROR: {e}")

    # INJECT LITE TOOLS
    if gmail_api and calendar_api:
        @tool
        def check_email_lite():
            """Returns unread count and top 5 snippets."""
            try:
                results = gmail_api.users().messages().list(userId='me', q="is:unread", maxResults=5).execute()
                messages = results.get('messages', [])
                total_unread = results.get('resultSizeEstimate', 0)
                if not messages: return "✅ 0 Unread Messages."
                report = f"📬 **INBOX REPORT** ({total_unread} Unread)\n"
                for msg in messages:
                    txt = gmail_api.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
                    headers = txt['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown").split('<')[0].strip().replace('"', '')
                    report += f"- **{sender}**: {subject}\n"
                return report
            except Exception as e: return f"Error: {e}"

        @tool
        def check_calendar_lite(days: int = 7):
            """Checks calendar for upcoming events."""
            try:
                now = datetime.datetime.utcnow()
                end = now + datetime.timedelta(days=days)
                events_result = calendar_api.events().list(calendarId='primary', timeMin=now.isoformat() + 'Z', timeMax=end.isoformat() + 'Z', maxResults=10, singleEvents=True, orderBy='startTime').execute()
                events = events_result.get('items', [])
                if not events: return f"📅 No events found for the next {days} days."
                summary = f"📅 **CALENDAR REPORT** (Next {days} Days)\n"
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    summary += f"- **{start}**: {event['summary']}\n"
                return summary
            except Exception as e: return f"Calendar Error: {e}"

        from langchain_google_community.gmail.send_message import GmailSendMessage
        from langchain_google_community.calendar.create_event import CalendarCreateEvent
        tools.extend([check_email_lite, check_calendar_lite, GmailSendMessage(api_resource=gmail_api), CalendarCreateEvent(api_resource=calendar_api)])
    else:
        @tool
        def check_email_lite(): return "📬 (SIMULATED) 3 Unread"
        @tool
        def check_calendar_lite(days: int = 7): return "📅 (SIMULATED) No upcoming events."
        tools.extend([check_email_lite, check_calendar_lite])

    return tools

# Initialize
tools = get_genesis_tools()
SENSITIVE_TOOLS = ["send_gmail_message", "create_calendar_event"]

# --- 3. STATE ---
class GenesisState(TypedDict):
    messages: Sequence[BaseMessage]
    permission_status: str 

@st.cache_resource(show_spinner="Booting Kernel...")
def setup_genesis_engine():
    umb_instance = get_memory_bus()
    # RAW BRAIN (No Tools)
    llm_raw = ChatGroq(groq_api_key=get_api_key(), model="llama-3.3-70b-versatile", temperature=0.1)
    # TOOL BRAIN (With Tools)
    llm_bound = llm_raw.bind_tools(tools)
    return llm_raw, llm_bound, umb_instance

llm_raw, llm_with_tools, umb = setup_genesis_engine()

# --- 4. PERMISSION GATE ---
def permission_router(state: GenesisState):
    if state.get("permission_status") == "pending":
        content = state["messages"][-1].content or ""
        if any(w in content.lower() for w in ["yes", "ok", "proceed"]): return {"permission_status": "granted"}
        return {"permission_status": "denied", "messages": [SystemMessage(content="Cancelled.")]}

    last_msg = state["messages"][-1]
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        if state.get("permission_status") == "granted": return {"permission_status": "reset"}
        for tc in last_msg.tool_calls:
            if "check_" in tc.get('name') or "research" in tc.get('name'): return {"permission_status": "reset"}
            if tc.get('name') in SENSITIVE_TOOLS: return {"permission_status": "pending", "messages": [SystemMessage(content=f"🔒 **AUTHORIZE:** {tc.get('name')}?")]}
    return {"permission_status": "neutral"}

# --- 5. PLANNER (KEYWORD SWITCH) ---
def planner_agent(state: GenesisState):
    messages = state['messages']
    last_msg = messages[-1]
    
    # 1. RETRIEVE MEMORY
    last_human_text = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "").lower()
    
    # 2. DEFINITIVE SAFETY SWITCH
    # We define keywords that indicate a DESIRE for action.
    action_keywords = ["check", "read", "scan", "find", "search", "research", "book", "schedule", "create", "send", "email", "calendar", "what is", "event"]
    
    # A. Check for Tool Output (Must summarize)
    if isinstance(last_msg, ToolMessage):
        sys_msg = SystemMessage(content="**DATA RECEIVED.** Summarize the findings briefly. STOP.")
        agent_llm = llm_raw # Switch to raw to prevent looping

    # B. Check for Action Keywords in User Input
    elif any(kw in last_human_text for kw in action_keywords):
        sys_msg = SystemMessage(content="**COMMAND MODE.** Use the requested tool immediately.")
        agent_llm = llm_with_tools # Give tools only if keyword found

    # C. Default to Chat (No Tools)
    else:
        sys_msg = SystemMessage(content="**CHAT MODE.** You are a helpful assistant. Reply with text only. Do NOT use tools.")
        agent_llm = llm_raw # Physically remove tools

    final_msgs = [sys_msg] + [m for m in messages if not isinstance(m, SystemMessage)]
    try:
        return {"messages": [agent_llm.invoke(final_msgs)]}
    except Exception as e:
        return {"messages": [HumanMessage(content=f"KERNEL ERROR: {e}")]}

# --- 6. GRAPH ---
workflow = StateGraph(GenesisState)
workflow.add_node("planner", planner_agent)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("permission_gate", permission_router)
workflow.set_entry_point("planner")

def route(state: GenesisState):
    if state.get("permission_status") == "pending": return "permission_gate"
    if hasattr(state["messages"][-1], 'tool_calls') and state["messages"][-1].tool_calls: return "permission_gate"
    return END

def perm_route(state: GenesisState):
    if state.get("permission_status") == "granted": return "planner"
    if state.get("permission_status") == "reset": return "tools"
    if state.get("permission_status") == "pending": return END
    return END

workflow.add_conditional_edges("planner", route)
workflow.add_conditional_edges("permission_gate", perm_route)
workflow.add_edge("tools", "planner")

app = workflow.compile(checkpointer=MemorySaver())

# --- 7. RUNNER ---
def run_genesis_agent(user_input: str):
    config = {"configurable": {"thread_id": "genesis_v2_final"}, "recursion_limit": 20}
    if user_input: umb.save_memory(user_input, {"type": "user_input"})
    current = app.get_state(config)
    if current.values.get("permission_status") == "pending":
        app.update_state(config, {"messages": [HumanMessage(content=user_input)]})
        inputs = None
    else:
        inputs = {"messages": [HumanMessage(content=user_input)], "permission_status": ""}
    for event in app.stream(inputs, config=config): yield event
