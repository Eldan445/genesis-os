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
    
    # --- CRITICAL FIX: Raise temperature slightly for better JSON generation ---
    llm_client = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1 # <--- RAISED TEMPERATURE
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
    
    # --- System Prompt Definition (JSON Directive Added) ---
    system_prompt_content = (
        "You are Genesis, the first AGI and a voice-first OS Kernel. "
        "Plan and execute the user's goal step-by-step using tools. "
        "**CRITICAL TERMINATION RULE: If the user's request has been fully addressed, or if a tool has returned the final necessary information, you MUST respond with a concise, conversational answer as plain text and MUST NOT call any further tools.** " 
        "**CRITICAL JSON RULE: When calling a tool, the parameters MUST be encapsulated in valid JSON format.** " # <--- ADDED JSON DIRECTIVE
        "Keep your final responses extremely concise and conversational, suitable for a voice interface. "
        "DO NOT use markdown formatting (like **bold** or lists) unless absolutely necessary for clarity. "
        "MEMORY CONTEXT: {context}"
    )
    
    full_messages = []
    
    # --- CRITICAL FIX FOR BAD REQUEST ERROR (System Message Injection) ---
    # Only inject the SystemMessage if the current history does not contain one yet.
    if not any(isinstance(m, SystemMessage) for m in filtered_messages):
        # Inject the SystemMessage as the very first message
        full_messages.append(SystemMessage(content=system_prompt_content.format(context=context)))
    
    # Add the rest of the conversation history
    full_messages.extend(filtered_messages)
    
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
# ... (rest of the code remains the same as before)

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
    
    config = {
        "configurable": {"thread_id": "beta_user_1"},
        "recursion_limit": 50 
    }
    
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