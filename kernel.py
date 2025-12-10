# kernel.py
import streamlit as st
import os
from dotenv import load_dotenv
from typing import TypedDict, Sequence
# Import Groq instead of Google Generative AI
from langchain_groq import ChatGroq 
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from umb import UniversalMemoryBus
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import MemorySaver

# --- 1. Load Environment Variables & Force Streamlit Secret ---
load_dotenv()

# CRITICAL FIX: Ensure the Streamlit secret is loaded into the OS environment
# This is a safeguard against Streamlit/OS caching issues.
# It prioritizes the Groq key now.
if os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

if not os.getenv("GROQ_API_KEY"):
    print("❌ ERROR: GROQ_API_KEY not found. Streamlit Secret is likely missing or named incorrectly.")


# --- 2. Define Tools ---
search_engine = DuckDuckGoSearchRun()

# IMPORTANT: Names of the REAL, natively available tools
SENSITIVE_TOOLS = [
    "generic_calendar:create",
    "generic_calendar:modify",
    "generic_calendar:delete",
    "generic_calendar:search",
    "gemkick_corpus:search"    # Represents email/document search
]

@tool
def research_tool(query: str):
    """Search the web for real-time information (prices, news, facts)."""
    try:
        return search_engine.run(query)
    except Exception as e:
        return f"Search failed: {e}"

tools = [research_tool]

# --- 3. Define State (Includes Permission Tracking) ---
class GenesisState(TypedDict):
    messages: Sequence[BaseMessage]
    context: str
    plan_status: str
    permission_status: str # Options: "pending", "granted", "denied" 

# --- 4. Cached Resource Initialization ---
@st.cache_resource(show_spinner="Booting Genesis Kernel...")
def setup_genesis_engine():
    """Initializes and caches the heavy AI components ONLY ONCE."""
    print("⚡ [KERNEL] Booting System & Loading Memory Bus (via Groq)...")
    
    memory_bus = UniversalMemoryBus()
    
    # --- CRITICAL CHANGE: Use Llama 3.1 8B Instant for stable tool use ---
    llm_client = ChatGroq(
        # Switched from deprecated mixtral to llama-3.1-8b-instant
        model="llama-3.1-8b-instant", # <--- UPDATED MODEL ID
        temperature=0
    )
    llm_with_tools_bound = llm_client.bind_tools(tools)
    
    print("✅ [KERNEL] System Ready.")
    return memory_bus, llm_with_tools_bound

# Initialize Resources
umb, llm_with_tools = setup_genesis_engine()

# --- 5. Agent Logic (PLANNER) ---
def planner_agent(state: GenesisState):
    messages = state['messages']
    
    # Filter messages to ensure only valid BaseMessage objects are passed
    filtered_messages = [msg for msg in messages if isinstance(msg, BaseMessage)]
    
    # Ensure there is at least one message for context retrieval
    last_user_msg = "User Request"
    if filtered_messages:
        for msg in reversed(filtered_messages):
            if not isinstance(msg, SystemMessage):
                last_user_msg = msg.content
                break
        
    try:
        context = umb.retrieve_context(last_user_msg)
    except Exception:
        context = "Memory ready."
    
    system_prompt = (
        "You are Genesis, the first AGI and a voice-first OS Kernel. "
        "Plan and execute the user's goal step-by-step using tools. "
        "Keep your final responses extremely concise and conversational, suitable for a voice interface. "
        "DO NOT use markdown formatting (like **bold** or lists) unless absolutely necessary for clarity. "
        "MEMORY CONTEXT: {context}"
    )
    
    # Prepend the system prompt to the filtered history
    full_messages = [SystemMessage(content=system_prompt.format(context=context))] + filtered_messages
    
    if not any(isinstance(m, HumanMessage) for m in full_messages):
        full_messages.append(HumanMessage(content="System initialized. Waiting for command."))

    # CRITICAL LINE: Invoke the LLM
    response = llm_with_tools.invoke(full_messages)
    
    try:
        umb.save_memory(response.content[:50], {"type": "log"})
    except:
        pass
    
    return {"messages": [response], "context": context, "plan_status": "Processing"}


# --- 6. Permission Agent (HUMAN-IN-THE-LOOP GATE) ---
def permission_router(state: GenesisState):
    """
    Checks if the tool call requires permission and handles the Human-in-the-Loop gate.
    """
    
    # 1. CHECK for Pending Permission (i.e., user is replying to the permission request)
    if state.get("permission_status") == "pending":
        last_message = state["messages"][-1].content.lower()
        if "yes" in last_message or "ok" in last_message or "allow" in last_message:
            return {"permission_status": "granted", "messages": [SystemMessage(content="Permission granted. Continuing plan.")]}
        else:
            return {"permission_status": "denied", 
                    "messages": [SystemMessage(content="Action cancelled by user permission.")]}

    # 2. CHECK for New Sensitive Tool Call (Planner just returned a tool call)
    last_message = state["messages"][-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call.get('name') in SENSITIVE_TOOLS: 
                app_name = tool_call.get('name').split(':')[0].replace('_', ' ').title()
                return {"permission_status": "pending", 
                        "messages": [SystemMessage(content=f"🔒 Genesis needs permission to use your **{app_name}** app. Please type **'OK'** to proceed or **'No'** to cancel.")]}
        
        return {"permission_status": "granted"}
    
    return {"permission_status": "denied"}


# --- 7. Build Graph and Routing ---
workflow = StateGraph(GenesisState)
workflow.add_node("planner", planner_agent)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("permission_gate", permission_router)

workflow.set_entry_point("planner")

# Routing function handles where to go next based on planner and permission status
def route_to_execution(state: GenesisState):
    status = state.get("permission_status")
    
    if status == "pending":
        return "permission_gate" 
        
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "permission_gate" 
        
    return END

# --- Define Edges ---

workflow.add_conditional_edges("planner", route_to_execution)

def route_from_permission_gate(state: GenesisState):
    status = state.get("permission_status")
    
    if status == "granted":
        return "tools"
    elif status == "pending":
        return "await_user_input"
    else: # "denied"
        return END

workflow.add_conditional_edges("permission_gate", route_from_permission_gate)

workflow.add_edge("tools", "planner")

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# --- 8. Export Function ---
def run_genesis_agent(user_input: str):
    config = {"configurable": {"thread_id": "beta_user_1"}}
    
    inputs = {
        "messages": [HumanMessage(content=user_input)], 
        "context": "", 
        "plan_status": "Starting",
        "permission_status": ""
    }
    
    current_state = app.get_state(config)
    
    if current_state.next and 'await_user_input' in current_state.next:
        app.update_state(config, {"messages": [HumanMessage(content=user_input)], "permission_status": "pending"})
        for event in app.stream(None, config=config):
            yield event
            
    else:
        for event in app.stream(inputs, config=config):
            yield event