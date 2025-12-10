# kernel.py
import streamlit as st
import os
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

# --- 1. Load Environment Variables & Robust Auth ---
load_dotenv()

def get_api_key():
    """Robustly retrieve API Key from OS Env OR Streamlit Secrets."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            # Fallback for Streamlit Cloud
            key = st.secrets["GROQ_API_KEY"]
        except Exception:
            pass
    if not key:
        print("❌ FATAL: GROQ_API_KEY not found in Env or Secrets.")
    return key

# --- 2. Define Tools ---
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
    """Search the web for real-time information (prices, news, facts)."""
    try:
        return search_engine.run(query)
    except Exception as e:
        return f"Search failed: {e}"

tools = [research_tool]

# --- 3. Define State ---
class GenesisState(TypedDict):
    messages: Sequence[BaseMessage]
    context: str
    plan_status: str
    permission_status: str 

# --- 4. Cached Resource Initialization ---
@st.cache_resource(show_spinner="Booting Genesis Kernel...")
def setup_genesis_engine():
    print("⚡ [KERNEL] Booting System...")
    
    # 1. Get Key
    groq_api_key = get_api_key()
    
    memory_bus = UniversalMemoryBus()
    
    # 2. Initialize Client with CORRECT Model
    try:
        llm_client = ChatGroq(
            groq_api_key=groq_api_key,
            model="llama-3.3-70b-versatile", # Confirmed supported model
            temperature=0.1
        )
        llm_with_tools_bound = llm_client.bind_tools(tools)
    except Exception as e:
        print(f"❌ Error initializing ChatGroq: {e}")
        raise e
    
    print("✅ [KERNEL] System Ready.")
    return memory_bus, llm_with_tools_bound

# Initialize Resources
umb, llm_with_tools = setup_genesis_engine()

# --- 5. Permission Agent (Defined BEFORE Graph) ---
def permission_router(state: GenesisState):
    """Human-in-the-Loop Gate"""
    if state.get("permission_status") == "pending":
        last_message = state["messages"][-1].content.lower()
        if "yes" in last_message or "ok" in last_message or "allow" in last_message:
            return {"permission_status": "granted", "messages": [SystemMessage(content="Permission granted. Continuing.")]}
        else:
            return {"permission_status": "denied", "messages": [SystemMessage(content="Action cancelled.")]}

    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.get('name') in SENSITIVE_TOOLS: 
                app_name = tool_call.get('name').split(':')[0].replace('_', ' ').title()
                return {"permission_status": "pending", 
                        "messages": [SystemMessage(content=f"🔒 Permission required for **{app_name}**. Type 'OK' to proceed.")]}
        return {"permission_status": "granted"}
    
    return {"permission_status": "denied"}

# --- 6. Agent Logic (PLANNER) ---
def planner_agent(state: GenesisState):
    messages = state['messages']
    
    # 1. Sanitize Messages (Remove duplicates, ensure valid types)
    sanitized_messages = []
    for msg in messages:
        if isinstance(msg, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
            sanitized_messages.append(msg)
            
    # 2. Retrieve Context
    last_user_msg = "User Request"
    for msg in reversed(sanitized_messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break
            
    try:
        context = umb.retrieve_context(last_user_msg)
    except:
        context = "Ready."
    
    # 3. Construct System Prompt
    system_prompt = (
        "You are Genesis, a voice-first AI OS. "
        "Execute the user's goal using tools if needed. "
        "**CRITICAL:** If you have the answer, output plain text. Do NOT call a tool again. "
        "**JSON RULE:** Ensure tool arguments are valid JSON. "
        "Context: {context}"
    )
    
    # 4. Inject System Message (Ensuring it's first)
    final_messages = [SystemMessage(content=system_prompt.format(context=context))]
    
    # Append history (skipping old system messages to avoid confusion)
    for m in sanitized_messages:
        if not isinstance(m, SystemMessage):
            final_messages.append(m)
            
    if not any(isinstance(m, HumanMessage) for m in final_messages):
        final_messages.append(HumanMessage(content="System initialized."))

    # 5. Invoke LLM
    response = llm_with_tools.invoke(final_messages)
    
    return {"messages": [response], "context": context, "plan_status": "Processing"}

# --- 7. Build Graph ---
workflow = StateGraph(GenesisState)
workflow.add_node("planner", planner_agent)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("permission_gate", permission_router)

workflow.set_entry_point("planner")

def route_to_execution(state: GenesisState):
    status = state.get("permission_status")
    if status == "pending": return "permission_gate" 
    
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "permission_gate" 
    return END

workflow.add_conditional_edges("planner", route_to_execution)

def route_from_permission_gate(state: GenesisState):
    status = state.get("permission_status")
    if status == "granted": return "tools"
    elif status == "pending": return "await_user_input"
    else: return END

workflow.add_conditional_edges("permission_gate", route_from_permission_gate)
workflow.add_edge("tools", "planner")

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# --- 8. Export Function ---
def run_genesis_agent(user_input: str):
    config = {"configurable": {"thread_id": "beta_user_1"}, "recursion_limit": 50}
    inputs = {"messages": [HumanMessage(content=user_input)], "context": "", "plan_status": "Starting", "permission_status": ""}
    
    current_state = app.get_state(config)
    if current_state.next and 'await_user_input' in current_state.next:
        app.update_state(config, {"messages": [HumanMessage(content=user_input)], "permission_status": "pending"})
        for event in app.stream(None, config=config): yield event
    else:
        for event in app.stream(inputs, config=config): yield event