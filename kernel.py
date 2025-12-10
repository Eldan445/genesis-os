# kernel.py
import streamlit as st
import os
from dotenv import load_dotenv
from typing import TypedDict, Sequence
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from umb import UniversalMemoryBus
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import MemorySaver 

# --- 1. Load Environment Variables ---
load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    print("❌ ERROR: GEMINI_API_KEY not found. Please check your .env file.")

# --- 2. Define Tools ---

# Search tool for research
search_engine = DuckDuckGoSearchRun()

# IMPORTANT: Names of the REAL, natively available tools. 
# These are the functions the LLM sees and calls.
SENSITIVE_TOOLS = [
    # CALENDAR TOOLS
    "generic_calendar:create_event", # Tool name 1
    "generic_calendar:modify_event", # Tool name 2
    "generic_calendar:delete_event", # Tool name 3
    "generic_calendar:search_events",# Tool name 4
    
    # EMAIL/DRIVE TOOLS
    "gemkick_corpus:search",         # Represents searching email/documents
    "gemkick_corpus:send_email"      # Represents sending an email
]

# 2.1. Tool Definitions (Only mock tools are implemented here, as the LLM
# handles the actual function call structure for the sensitive tools)

@tool
def research_tool(query: str):
    """Search the web for real-time information (prices, news, facts)."""
    try:
        return search_engine.run(query)
    except Exception as e:
        return f"Search failed: {e}"

@tool
def generic_calendar_create_event(title: str, start_time: str, end_time: str, attendees: list[str]) -> str:
    """Creates a new calendar event with the specified title, times, and list of attendees."""
    # In a real app, this would call the Google Calendar API
    return f"Created event '{title}' from {start_time} to {end_time} with attendees: {', '.join(attendees)}."

@tool
def generic_calendar_modify_event(event_id: str, new_title: str | None = None, new_time: str | None = None) -> str:
    """Modifies an existing calendar event using its unique ID."""
    return f"Modified event ID {event_id}. Changes applied."

@tool
def generic_calendar_delete_event(event_id: str) -> str:
    """Deletes a calendar event using its unique ID."""
    return f"Deleted event ID {event_id}."

@tool
def generic_calendar_search_events(query: str) -> str:
    """Searches the user's calendar for events matching the query."""
    return f"Searching calendar for: '{query}'. Found 2 matching events."

@tool
def gemkick_corpus_search(query: str) -> str:
    """Searches the user's email, documents, and drive files for content matching the query."""
    return f"Searching user data corpus for: '{query}'. Found 3 relevant emails."

@tool
def gemkick_corpus_send_email(recipient: str, subject: str, body: str) -> str:
    """Composes and sends an email to the specified recipient."""
    return f"Drafted email to {recipient} with subject '{subject}'. Waiting for user approval to send."


# Combine ALL tools, sensitive and non-sensitive, for the LLM to choose from
tools = [
    research_tool,
    generic_calendar_create_event,
    generic_calendar_modify_event,
    generic_calendar_delete_event,
    generic_calendar_search_events,
    gemkick_corpus_search,
    gemkick_corpus_send_email
]

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
    print("⚡ [KERNEL] Booting System & Loading Memory Bus...")
    
    memory_bus = UniversalMemoryBus()
    # Use gemini-2.5-flash for better tool calling reliability
    llm_client = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    llm_with_tools_bound = llm_client.bind_tools(tools)
    
    print("✅ [KERNEL] System Ready.")
    return memory_bus, llm_with_tools_bound

# Initialize Resources
umb, llm_with_tools = setup_genesis_engine()

# --- 5. Agent Logic (PLANNER) ---
def planner_agent(state: GenesisState):
    messages = state['messages']
    
    last_user_msg = "User Request"
    if messages:
        # Find the content of the most recent HumanMessage
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break
        
    try:
        context = umb.retrieve_context(last_user_msg)
    except Exception:
        context = "Memory ready."
    
    system_prompt = (
        "You are Genesis, the first AGI and a voice-first OS Kernel. "
        "Plan and execute the user's goal step-by-step using the provided tools. "
        "Keep your final responses extremely concise and conversational, suitable for a voice interface. "
        "DO NOT use markdown formatting (like **bold** or lists) unless absolutely necessary for clarity. "
        "MEMORY CONTEXT: {context}"
    )
    
    # FIX: Define full_messages BEFORE it is used in the loop below
    full_messages = [SystemMessage(content=system_prompt.format(context=context))] + messages
    
    # Crucial: Filter out the previous SystemMessage permission request, 
    # but ensure the *HumanMessage reply* is included.
    filtered_messages = []
    has_system_prompt = False
    
    for msg in full_messages: # This is now safe
        if isinstance(msg, SystemMessage) and not has_system_prompt:
            filtered_messages.append(msg)
            has_system_prompt = True
        elif not isinstance(msg, SystemMessage):
             filtered_messages.append(msg)
             
    # Use the filtered list for the LLM invocation
    response = llm_with_tools.invoke(filtered_messages)
    
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
        # The user's reply is the last message added by run_genesis_agent
        last_message = state["messages"][-1].content.lower()
        if "yes" in last_message or "ok" in last_message or "allow" in last_message:
            # FIX: Only return the status update. The router will send it to 'tools'
            return {"permission_status": "granted"}
        else:
            # Permission Denied. End the execution.
            return {"permission_status": "denied", 
                    "messages": [SystemMessage(content="Action cancelled by user permission.")]}

    # 2. CHECK for New Sensitive Tool Call (Planner just returned a tool call)
    last_message = state["messages"][-1]
    
    # Check if the message has tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        # Check all tool calls suggested by the LLM
        for tool_call in last_message.tool_calls:
            # FIX: Access the name using dictionary key 'name' instead of object attribute
            tool_name = tool_call.get('name')
            
            if tool_name in SENSITIVE_TOOLS: 
                # Interrupt the flow and update the state to "pending".
                app_name = tool_name.split(':')[0].replace('_', ' ').title()
                
                # Check for specific action in tool name for better prompt
                action = tool_name.split(':')[-1].replace('_', ' ').title()
                
                return {"permission_status": "pending", 
                        "messages": [SystemMessage(content=f"🔒 Genesis needs permission to **{action}** in your **{app_name}** app. Please type **'OK'** to proceed or **'No'** to cancel.")]}
        
        # If no sensitive tools were found, allow execution
        return {"permission_status": "granted"}
    
    # Fallback: If no tool call, the planner just returned a text response
    return {"permission_status": "denied"} # Setting to denied here makes the route_to_execution go to END

# --- 7. Build Graph and Routing ---
workflow = StateGraph(GenesisState)
workflow.add_node("planner", planner_agent)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("permission_gate", permission_router)

workflow.set_entry_point("planner")

# Routing function handles where to go next based on planner and permission status
def route_to_execution(state: GenesisState):
    # Reroute after user input (permission) back to the gate
    if state.get("permission_status") == "pending":
        return "permission_gate" 
        
    # Planner output routes to permission gate if tool call is detected
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "permission_gate" 
        
    # Plan complete
    return END

# --- Define Edges ---

# 1. Planner always routes to permission_gate if a tool call is detected
workflow.add_conditional_edges("planner", route_to_execution)

# 2. Permission Gate Routes to Tools (if granted) or END/Pause (if pending/denied)
def route_from_permission_gate(state: GenesisState):
    status = state.get("permission_status")
    
    if status == "granted":
        return "tools"
    elif status == "pending":
        # This is the interrupt signal: the agent pauses and waits for user input.
        return "await_user_input"
    else: # "denied"
        return END

workflow.add_conditional_edges("permission_gate", route_from_permission_gate)

# 3. After Tool Execution, always return to the planner to continue the plan
workflow.add_edge("tools", "planner")

# Initialize an in-memory checkpointer for HITL
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# --- 8. Export Function ---
# This function must be at the top level and correctly named for genesis_ui.py to import it.
def run_genesis_agent(user_input: str):
    # We must provide a thread_id for the checkpointer to track the state
    config = {"configurable": {"thread_id": "beta_user_1"}}
    
    inputs = {
        "messages": [HumanMessage(content=user_input)], 
        "context": "", 
        "plan_status": "Starting",
        "permission_status": ""
    }
    
    # Get the current state using the checkpointer configuration
    current_state = app.get_state(config)
    
    if current_state.next and 'await_user_input' in current_state.next:
        # If paused (waiting for user reply, e.g., 'OK'), update state with the new message
        
        # 1. Inject the user's reply (the permission grant/deny) into the message history
        # This updates the state BEFORE the resume stream starts.
        # It also sets permission_status back to "pending" to trigger the permission_router check
        inputs_for_resume = {"messages": [HumanMessage(content=user_input)], "permission_status": "pending"}
        app.update_state(config, inputs_for_resume) 
        
        # 2. Resume execution from the paused state, starting from the next node (permission_gate)
        # We pass an empty dict as input to stream() since the state has already been updated.
        for event in app.stream({}, config=config):
            yield event
            
    else:
        # Normal start: stream with initial inputs
        for event in app.stream(inputs, config=config):
            yield event