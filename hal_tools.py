# hal_tools.py
from langchain.tools import tool

@tool
def research_tool(query: str):
    """Simulates browsing the web for information."""
    # In Wedge 3, this will be real. Now, it's a mock.
    print(f"🌍 [HAL] Research Tool Activated: Searching for '{query}'")
    return f"Simulated research data found for: {query}. Competitor prices are up 5%."

@tool
def calendar_tool(event_details: str):
    """Simulates scheduling an event on the system calendar."""
    print(f"📅 [HAL] Calendar Tool Activated: Scheduling '{event_details}'")
    return "Event successfully scheduled for Friday at 2 PM."

# List for the Agent to access
tools = [research_tool, calendar_tool]