import os
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from .state import FarmerState
from .tools import search_treatments_tool, get_weather_tool, search_schemes_tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from config import AGENT_MODEL

# Ensure the API key is set in the environment for the provider
os.environ.setdefault("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

# ── LLM initialisation ────────────────────────────────────────────────────────
# init_chat_model reads the provider from the "provider/model" string in config.
# To switch models, change AGENT_MODEL in config.py — no code changes needed.
# Examples:
#   "google_genai/gemini-2.0-flash"
#   "openai/gpt-4o"
#   "anthropic/claude-3-5-sonnet-20241022"
#   "groq/llama-3.3-70b-versatile"
tools = [search_treatments_tool, get_weather_tool, search_schemes_tool]

# Split "provider/model-name" into separate args for init_chat_model
_parts = AGENT_MODEL.split("/", 1)
_provider = _parts[0] if len(_parts) == 2 else None
_model_name = _parts[1] if len(_parts) == 2 else AGENT_MODEL

llm = init_chat_model(_model_name, model_provider=_provider).bind_tools(tools)
tool_node = ToolNode(tools)


def should_continue(state: FarmerState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def call_model(state: FarmerState):
    messages = state["messages"]
    system_prompt = SystemMessage(content=f"""
You are an expert agricultural advisor for Indian farmers.
The farmer you are talking to:
- Name: {state.get('name', 'Unknown')}
- Location: {state.get('location', 'Unknown')}
- Main crop: {state.get('crop', 'Unknown')}

Always personalize your advice based on their location and crop.
If asked for disease treatment, ALWAYS use the `search_treatments_tool`. Do not suggest pesticide brands yourself.
If asked for weather advice, use `get_weather_tool`.
If asked for government schemes, use `search_schemes_tool`.
Respond in the same language the farmer is using.
Keep answers under 250 words.
""")
    response = llm.invoke([system_prompt] + messages)
    return {"messages": [response]}


workflow = StateGraph(FarmerState)

# Define nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Set entry point
workflow.set_entry_point("agent")

# Add edges
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

# Compile graph
app = workflow.compile()
