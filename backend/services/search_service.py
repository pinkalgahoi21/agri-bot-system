import google.generativeai as genai
from config import GOOGLE_API_KEY, AI_MODEL

genai.configure(api_key=GOOGLE_API_KEY)

def search_schemes(crop, location):
    """Use Gemini AI to generate relevant schemes - no internet needed"""

    prompt = f"""List the most important and current Indian government schemes 
for a {crop} farmer in {location}.

For each scheme provide:
- Scheme name
- Benefit amount or subsidy
- Eligibility criteria  
- How to apply (website or office)
- Whether it is central or state scheme

Include both central government schemes (PM-KISAN, KCC, PMFBY etc.) 
and any UP/Uttar Pradesh state specific schemes if location is UP.

Give at least 6-7 schemes. Be specific with amounts and websites."""

    try:
        model = genai.GenerativeModel(
            model_name=AI_MODEL,
            system_instruction="You are an expert on Indian agricultural government schemes. Give accurate, detailed, practical information about schemes available for farmers.",
        )
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"AI scheme generation error: {e}")
        return None