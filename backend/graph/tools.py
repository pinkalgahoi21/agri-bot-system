from langchain_core.tools import tool
from services.rag_service import search_rag
from services.search_service import search_schemes
from services.weather_service import get_weather

@tool
def search_treatments_tool(disease: str, crop: str) -> str:
    """
    Searches the official ICAR CIBRC database for verified treatments for a given disease and crop.
    Use this tool whenever the user asks for pesticide/fungicide treatments or asks how to cure a disease.
    """
    results = search_rag(disease, crop, n_results=3)
    if not results:
        return "No official treatments found for this disease in the database."
    
    # Format the results into a readable string for the LLM
    context = []
    for r in results:
        context.append(f"Document: {r['document']}\nMetadata: {r['metadata']}")
    return "\n\n".join(context)

@tool
def get_weather_tool(city: str) -> str:
    """
    Fetches the current weather and 48-hour forecast for a given city.
    Use this tool to give farming advice based on weather conditions (e.g., spraying, irrigation).
    """
    weather = get_weather(city)
    if not weather:
        return f"Could not fetch weather data for {city}."
    
    return f"Current Temp: {weather['temp']}C, Conditions: {weather['description']}, Rain: {weather['rain']}mm.\nForecast: {weather['forecast']}"

@tool
def search_schemes_tool(crop: str, location: str) -> str:
    """
    Searches DuckDuckGo for the latest government schemes related to a specific crop and location.
    Use this tool when the user asks about subsidies, schemes, or financial help.
    """
    results = search_schemes(crop, location)
    if not results:
        return "No recent schemes found."
    return results
