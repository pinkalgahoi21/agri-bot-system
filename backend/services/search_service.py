from groq import Groq
from config import GROQ_API_KEY, AI_MODEL

client = Groq(api_key=GROQ_API_KEY)

def search_schemes(crop, location):
    """Use Groq AI to generate relevant schemes - no internet needed"""

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
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert on Indian agricultural government schemes. Give accurate, detailed, practical information about schemes available for farmers."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"AI scheme generation error: {e}")
        return None