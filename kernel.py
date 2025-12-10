# kernel.py
import streamlit as st
import os
import uuid
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

# --- 1. Robust Auth ---
load_dotenv()

def get_api_key():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    return key

# --- 2. Define Tools (Llama-Optimized) ---
search_engine = DuckDuckGoSearchRun()

SENSITIVE_TOOLS = [
    "generic_calendar:create",
    "generic_calendar:modify",
    "generic_calendar:delete",
    "generic_calendar:search",
    "gemkick_corpus:search"
]

@tool
def research_tool(query: str):
    """
    Perform a web search to find real-time information, news, or facts.
    
    Args:
        query: The search string to look up.
    """
    try:
        return search_engine.run(query)
    except Exception as e:
        return f"Search failed: {e}"

tools = [research_tool]

# --- 3. State Definition ---
class GenesisState(TypedDict):
    messages: Sequence[BaseMessage]
    context: str
    plan_status: str
    permission_status: str 

# --- 4. Engine Initialization ---
@st.cache_resource(show_spinner="Booting Genesis Kernel...")
def setup_genesis_engine():
    print("⚡ [KERNEL] Booting...")
    groq_api_key = get_api_key()
    
    if not groq_api_key:
        print("❌ FATAL: No API Key found.")
    
    memory_bus = UniversalMemoryBus()
    
    # Primary Client (Tool Aware)
    llm_client = ChatGroq(
        groq_api_key=groq_api_key,
        model="llama-3.3-70b-versatile", 
        temperature=0.1
    )
    llm_with_tools_bound = llm_client.bind_tools(tools)
    
    # Fallback Client (Chat Only - No Tools)
    llm_fallback = ChatGroq(
        groq_api_key=groq_api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.3
    )
    
    print("✅ [KERNEL] Ready.")
    return memory_bus, llm_with_tools_bound, llm_fallback

# Initialize
umb, llm_with_tools, llm_fallback = setup_genesis_engine()

# --- 5. Permission Gate ---
def permission_router(state: GenesisState):
    if state.get("permission_status") == "pending":
        last_msg = state["messages"][-1].content.lower()
        if any(w in last_msg for w in ["yes", "ok", "allow", "sure"]):
            return {"permission_status": "granted", "messages": [SystemMessage(content="Permission granted.")]}
        return {"permission_status": "denied", "messages": [SystemMessage(content="Denied.")]}

    last_msg = state["messages"][-1]
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        for tc in last_msg.tool_calls:
            if tc.get('name') in SENSITIVE_TOOLS:
                app = tc.get('name').split(':')[0].title()
                return {"permission_status": "pending", 
                        "messages": [SystemMessage(content=f"🔒 Allow access to {app}?")]}
        return {"permission_status": "granted"}
    return {"permission_status": "denied"}

# --- 6. Planner Agent (Bulletproof) ---
def planner_agent(state: GenesisState):
    messages = state['messages']
    
    # 1. Clean History (Remove corrupted/empty messages)
    clean_history = []
    for m in messages:
        if isinstance(m, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
            # Filter empty content if not a tool call
            if isinstance(m, AIMessage) and not m.content and not m.tool_calls:
                continue
            clean_history.append(m)

    # 2. Get Context
    try:
        last_human = next((m.content for m in reversed(clean_history) if isinstance(m, HumanMessage)), "User input")
        context = umb.retrieve_context(last_human)
    except:
        context = "Ready."

    # 3. System Prompt
    sys_msg = SystemMessage(content=(
        "You are Genesis, a voice-first AI OS. "
        "Use tools only if needed. "
        "**CRITICAL:** Output Valid JSON for tools. If answering, use plain text. "
        f"Context: {context}"
    ))
    
    # 4. Construct Final Message List
    final_msgs = [sys_msg] + [m for m in clean_history if not isinstance(m, SystemMessage)]
    
    # Ensure start
    if not any(isinstance(m, HumanMessage) for m in final_msgs):
        final_msgs.append(HumanMessage(content="System ready."))

    # 5. EXECUTION WITH FALLBACK (The Crash Prevention)
    try:
        # Try primary model with tools
        response = llm_with_tools.invoke(final_msgs)
    except Exception as e:
        print(f"⚠️ Tool Error: {e}. Switching to fallback.")
        # If 400 Error happens, FALLBACK to simple chat so demo continues
        fallback_msgs = final_msgs + [SystemMessage(content="Note: Tools unavailable. Answer directly.")]
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
    # CRITICAL: New Thread ID for Demo to clear corrupted history
    config = {"configurable": {"thread_id": "investor_demo_v1"}, "recursion_limit": 40}
    
    inputs = {"messages": [HumanMessage(content=user_input)], "context": "", "plan_status": "Starting", "permission_status": ""}
    
    current = app.get_state(config)
    if current.next and 'await_user_input' in current.next:
        app.update_state(config, {"messages": [HumanMessage(content=user_input)], "permission_status": "pending"})
        for event in app.stream(None, config=config): yield event
    else:
        for event in app.stream(inputs, config=config): yield event