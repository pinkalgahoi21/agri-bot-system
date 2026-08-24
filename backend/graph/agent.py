import os
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from .state import FarmerState
from .tools import search_treatments_tool, get_weather_tool, search_schemes_tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode

# Initialize LLM
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

# Tools
tools = [search_treatments_tool, get_weather_tool, search_schemes_tool]
llm = ChatGroq(model="llama3-70b-8192").bind_tools(tools)
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
