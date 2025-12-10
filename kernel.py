# kernel.py
import streamlit as st
import os
import json
from dotenv import load_dotenv
from typing import TypedDict, Sequence
from langchain_groq import ChatGroq 
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from umb import UniversalMemoryBus
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import MemorySaver

# --- 1. Robust Auth & Configuration ---
load_dotenv()

def get_api_key():
    """Retrieves API Key with Streamlit Cloud Fallback."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    return key

# --- 2. DEMO TOOLS (Real Search + Simulated Actions) ---

# A. Real Internet Search (Shows Genesis is smart/connected)
search_engine = DuckDuckGoSearchRun()

@tool
def research_tool(query: str):
    """
    Use this to search the internet for real-time information, news, prices, or facts.
    """
    try:
        return search_engine.run(query)
    except Exception as e:
        return f"Search error: {e}"

# B. Calendar Tool (Simulated for Stability)
@tool
def calendar_tool(event_details: str):
    """
    Use this to schedule meetings or events. 
    Input should include the event title and time (e.g., 'Meeting with Investors at 2 PM').
    """
    # In a real app, this would hit the Google Calendar API.
    # For the demo, we simulate success to prevent Auth crashes.
    return f"✅ SUCCESS: Calendar event '{event_details}' has been scheduled."

# C. Email Tool (Simulated for Stability)
@tool
def email_tool(recipient: str, subject: str, body: str):
    """
    Use this to send emails. 
    Requires recipient address, subject line, and body text.
    """
    # In a real app, this would hit the Gmail API.
    return f"✅ SUCCESS: Email sent to {recipient} with subject '{subject}'."

# List of tools available to the Agent
tools = [research_tool, calendar_tool, email_tool]

# SENSITIVE TOOLS LIST (Triggers the Permission Gate)
SENSITIVE_TOOLS = ["calendar_tool", "email_tool"]

# --- 3. State Definition ---
class GenesisState(TypedDict):
    messages: Sequence[BaseMessage]
    context: str
    plan_status: str
    permission_status: str 

# --- 4. Engine Initialization ---
@st.cache_resource(show_spinner="Booting Genesis Kernel...")
def setup_genesis_engine():
    print("⚡ [KERNEL] Booting System...")
    
    groq_api_key = get_api_key()
    if not groq_api_key:
        print("❌ FATAL: GROQ_API_KEY missing.")
    
    memory_bus = UniversalMemoryBus()
    
    # Primary Client (Tool Aware) - Using the CORRECT Llama 3.3 Model
    llm_client = ChatGroq(
        groq_api_key=groq_api_key,
        model="llama-3.3-70b-versatile", # <--- CORRECTED MODEL ID
        temperature=0.1
    )
    llm_with_tools_bound = llm_client.bind_tools(tools)
    
    # Fallback Client (Safety Net)
    llm_fallback = ChatGroq(
        groq_api_key=groq_api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.3
    )
    
    print("✅ [KERNEL] Ready.")
    return memory_bus, llm_with_tools_bound, llm_fallback

# Initialize
umb, llm_with_tools, llm_fallback = setup_genesis_engine()

# --- 5. Permission Gate (Human-in-the-Loop) ---
def permission_router(state: GenesisState):
    # 1. Check if user just granted permission
    if state.get("permission_status") == "pending":
        last_msg = state["messages"][-1].content.lower()
        if any(w in last_msg for w in ["yes", "ok", "allow", "sure", "proceed"]):
            return {"permission_status": "granted", "messages": [SystemMessage(content="Permission granted. Executing action.")]}
        return {"permission_status": "denied", "messages": [SystemMessage(content="Action cancelled.")]}

    # 2. Check if the Agent wants to use a sensitive tool
    last_msg = state["messages"][-1]
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        for tc in last_msg.tool_calls:
            if tc.get('name') in SENSITIVE_TOOLS:
                # Format a nice permission request
                tool_name = tc.get('name').replace('_tool', '').title()
                return {"permission_status": "pending", 
                        "messages": [SystemMessage(content=f"🔒 **Security Alert:** Genesis needs permission to access your **{tool_name}**. Proceed?")]}
        return {"permission_status": "granted"}
    
    return {"permission_status": "granted"}

# --- 6. Planner Agent ---
def planner_agent(state: GenesisState):
    messages = state['messages']
    
    # 1. Context Retrieval
    try:
        # Find last user message
        last_human = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
        context = umb.retrieve_context(last_human)
    except:
        context = "Ready."

    # 2. System Prompt (Strict Instructions)
    sys_msg = SystemMessage(content=(
        "You are Genesis, a voice-first AI OS. "
        "Use tools (Research, Calendar, Email) to fulfill requests. "
        "**CRITICAL:** When you are done, output plain text contextually. Do NOT call a tool again just to say goodbye. "
        f"Memory Context: {context}"
    ))
    
    # 3. Message Construction (Avoid duplicate SystemMessages)
    final_msgs = [sys_msg] + [m for m in messages if not isinstance(m, SystemMessage)]
    
    # Ensure conversation start
    if not any(isinstance(m, HumanMessage) for m in final_msgs):
        final_msgs.append(HumanMessage(content="System initialized."))

    # 4. Execution with Fallback
    try:
        response = llm_with_tools.invoke(final_msgs)
    except Exception as e:
        print(f"⚠️ Agent Error: {e}. Switching to fallback.")
        # If tool model fails, use fallback to keep demo alive
        fallback_msgs = final_msgs + [SystemMessage(content="Tools unavailable. Respond conversationally.")]
        response = llm_fallback.invoke(fallback_msgs)

    return {"messages": [response], "context": context, "plan_status": "Processing"}

# --- 7. Graph Setup ---
workflow = StateGraph(GenesisState)
workflow.add_node("planner", planner_agent)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("permission_gate", permission_router)

workflow.set_entry_point("planner")

def route_to_execution(state: GenesisState):
    if state.get("permission_status") == "pending": return "permission_gate"
    last = state["messages"][-1]
    if hasattr(last, 'tool_calls') and last.tool_calls: return "permission_gate"
    return END

def route_from_permission(state: GenesisState):
    status = state.get("permission_status")
    if status == "granted": return "tools"
    if status == "pending": return "await_user_input"
    return END

workflow.add_conditional_edges("planner", route_to_execution)
workflow.add_conditional_edges("permission_gate", route_from_permission)
workflow.add_edge("tools", "planner")

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# --- 8. Run Function ---
def run_genesis_agent(user_input: str):
    # New Thread ID to wipe any corrupted history for the demo
    config = {"configurable": {"thread_id": "investor_demo_v2"}, "recursion_limit": 40}
    
    inputs = {"messages": [HumanMessage(content=user_input)], "context": "", "plan_status": "Starting", "permission_status": ""}
    
    current = app.get_state(config)
    if current.next and 'await_user_input' in current.next:
        app.update_state(config, {"messages": [HumanMessage(content=user_input)], "permission_status": "pending"})
        for event in app.stream(None, config=config): yield event
    else:
        for event in app.stream(inputs, config=config): yield event