from langchain_core.tools import tool
from services.rag_service import search_rag
from services.vector_rag import search_pdf
import logging
from services.search_service import live_schemes
from services.weather_service import _fetch_weather

@tool
def search_treatments_tool(disease: str, crop: str) -> str:
    """
    Retrieves matching entries from a limited local crop-specific reference collection.
    Use this tool whenever the user asks for pesticide/fungicide treatments or asks how to cure a disease.
    """
    try:
        results = search_pdf(disease, crop)
    except Exception:
        logging.getLogger(__name__).exception("PDF vector lookup unavailable")
        results = []
    if results:
        return "PDF search excerpts. Cite filename and page. Table rows may be fragmented: do not infer product uses or doses from nearby rows.\n" + "\n\n".join(
            f"{hit['metadata']['source']}, page {hit['metadata']['page']}:\n{hit['document']}" for hit in results
        )
    results = search_rag(disease, crop, n_results=3)
    if not results:
        return "No official treatments found for this disease in the database."
    
    # Format the results into a readable string for the LLM
    context = []
    for r in results:
        context.append(f"Document: {r['document']}\nMetadata: {r['metadata']}")
    return "Curated catalogue fallback (no usable PDF hit):\n" + "\n\n".join(context)

@tool
def get_weather_tool(city: str) -> str:
    """
    Fetches current conditions and available three-hour forecast intervals for a given city.
    Use this tool to give farming advice based on weather conditions (e.g., spraying, irrigation).
    """
    weather = _fetch_weather(city)
    if not weather:
        return f"Could not fetch weather data for {city}."
    
    return (f"{weather['city']} now: {weather['temp']}°C, {weather['description']}; "
            f"humidity {weather['humidity']}%, wind {weather['wind_speed']} m/s, "
            f"rain in past hour {weather['rain']} mm.\nForecast (local time): {weather['forecast']}")

@tool
def search_schemes_tool(crop: str, location: str, topic: str = "agricultural schemes") -> str:
    """
    Provides official government scheme discovery and crop insurance portals for the farmer.
    Use this tool when the user asks about subsidies, schemes, or financial help.
    """
    results = live_schemes(crop, location, topic)
    if not results:
        return "No recent schemes found."
    return results
