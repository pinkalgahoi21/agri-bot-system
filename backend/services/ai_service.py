"""
services/ai_service.py
All Groq AI calls — chat, disease diagnosis, weather advice, RAG treatment.
"""
from __future__ import annotations
from groq import Groq
from pydantic import BaseModel, field_validator
from config import GROQ_API_KEY, AI_MODEL

client = Groq(api_key=GROQ_API_KEY)


# ── Shared disease result schema ───────────────────────────────────────────────
# Used by both identify_disease() (text) and analyze_crop_image() (vision).
# Both pipelines return the same dict shape — downstream code handles one format.

class DiseaseResult(BaseModel):
    disease:    str
    confidence: str
    severity:   str
    cause:      str
    prevention: list[str]
    urgency:    str

    @field_validator("confidence")
    @classmethod
    def _val_confidence(cls, v):
        return v if v in {"High", "Medium", "Low"} else "Low"

    @field_validator("severity")
    @classmethod
    def _val_severity(cls, v):
        return v if v in {"Mild", "Moderate", "Severe"} else "Unknown"

    @field_validator("urgency")
    @classmethod
    def _val_urgency(cls, v):
        return v if v in {"Immediate", "Within a week", "Monitor"} else "Monitor"


_DISEASE_FALLBACK: dict = {
    "disease":    "Unclear symptoms",
    "confidence": "Low",
    "severity":   "Unknown",
    "cause":      "Could not determine cause.",
    "prevention": ["Monitor crop closely", "Consult local KVK"],
    "urgency":    "Monitor",
}


# ── System prompt ─────────────────────────────────────────────────────────────

def get_system_prompt(profile: dict) -> str:
    return f"""You are an expert agricultural advisor for Indian farmers.

The farmer you are talking to:
- Name: {profile['name']}
- Location: {profile['location']}
- Main crop: {profile['crop']}

Always personalize your advice based on their location and crop.
Give simple, practical, actionable advice about:
- Crop selection and planting
- Soil health and irrigation
- Weather and season-based advice
- Pest and disease identification (symptoms, causes, prevention)
- Government schemes for farmers
- Fertilizer types and timing (NPK, organic, etc.)

STRICT RULES — follow without exception:
1. NEVER suggest specific pesticide or medicine brand names
   (e.g. Mancozeb, Carbendazim, Copper Hydroxide, Chlorpyrifos).
   If asked about treatment say:
   "Please use the /disease command for verified medicine recommendations
   from the official CIBRC database with correct dosage."
2. You may describe general prevention (remove infected leaves, improve drainage).
3. You may name fertilizer types (urea, DAP, potash) — NOT pesticide brands.
4. Respond in the same language the farmer is using.
5. Keep answers under 250 words.
6. If asked anything unrelated to farming, politely decline in the farmer's language."""


# ── General chat ───────────────────────────────────────────────────────────────

def get_ai_response(profile: dict, history: list, user_message: str) -> str:
    try:
        messages = [
            {"role": "system", "content": get_system_prompt(profile)}
        ] + history + [
            {"role": "user", "content": user_message}
        ]
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=600,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ai_service] get_ai_response error: {e}")
        return "Sorry, I couldn't process your request. Please try again."


# ── Schemes summariser ─────────────────────────────────────────────────────────

def summarize_schemes(profile: dict, search_text: str) -> str:
    prompt = f"""Based on these search results:

{search_text}

Farmer details:
- Name: {profile['name']}
- Location: {profile['location']}
- Main crop: {profile['crop']}

List 4-5 most relevant government schemes for this farmer.
For each scheme provide:
- 🏛️ Scheme name
- 💰 Main benefit with amount
- ✅ Who is eligible
- 📝 How to apply (website or office)

Keep it simple, clear and practical."""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a government scheme advisor for Indian farmers."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=700,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ai_service] summarize_schemes error: {e}")
        return "Sorry, couldn't fetch scheme information. Please try again."


# ── Disease diagnosis ──────────────────────────────────────────────────────────

def _parse_disease_output(raw: str) -> dict:
    """
    Parse structured plain text from identify_disease() into a validated dict.
    Shares the same DiseaseResult schema as image_service._parse_vision_output().
    """
    lines = raw.strip().splitlines()

    # Trim to Disease: line
    start = 0
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("disease:"):
            start = i
            break
    lines = lines[start:]

    def _extract(prefix: str, fallback: str) -> str:
        for line in lines:
            if line.strip().lower().startswith(prefix.lower()) and ":" in line:
                value = line.split(":", 1)[1].strip()
                if value:
                    return value
        return fallback

    # Prevention bullets
    prevention: list[str] = []
    in_prev = False
    for line in lines:
        s = line.strip()
        if s.lower().startswith("prevention"):
            in_prev = True
            continue
        if in_prev:
            if s.startswith(("•", "-", "*")):
                p = s.lstrip("•-* ").strip()
                if p:
                    prevention.append(p)
            elif s and ":" in s and not s[0].isspace():
                in_prev = False
    if not prevention:
        prevention = ["Monitor crop closely", "Consult local KVK"]

    raw_conf   = _extract("Confidence", "").title()
    confidence = raw_conf if raw_conf in {"High", "Medium", "Low"} else "Low"

    raw_sev  = _extract("Severity", "").title()
    severity = raw_sev if raw_sev in {"Mild", "Moderate", "Severe"} else "Unknown"

    raw_urg = _extract("Urgency", "").lower()
    urgency_map = {
        "immediate":     "Immediate",
        "within a week": "Within a week",
        "monitor":       "Monitor",
    }
    urgency = urgency_map.get(raw_urg, "Monitor")

    disease = _extract("Disease", "Unclear symptoms").strip() or "Unclear symptoms"
    cause   = _extract("Cause",   "Could not determine cause.").strip()

    try:
        return DiseaseResult(
            disease=disease,
            confidence=confidence,
            severity=severity,
            cause=cause,
            prevention=prevention,
            urgency=urgency,
        ).model_dump()
    except Exception:
        return _DISEASE_FALLBACK.copy()


def identify_disease(symptoms: str, crop: str, location: str) -> dict:
    """
    Identify disease from text symptoms.
    Returns a DiseaseResult-validated dict — same schema as analyze_crop_image().

    CRITICAL: returns dict, NOT str.
    disease.py, medicine_service.py, and format_diagnosis() all expect a dict.
    """
    prompt = f"""A farmer in {location} reports these symptoms on their {crop} crop:

{symptoms}

STRICT OUTPUT FORMAT (follow exactly, no changes):

Disease: <single most likely disease or pest name>
Confidence: <High / Medium / Low>
Severity: <Mild / Moderate / Severe>
Cause: <one short sentence>
Prevention:
• <point 1>
• <point 2>
• <point 3>
Urgency: <Immediate / Within a week / Monitor>

RULES:
- Line 1 MUST start with exactly "Disease: " (no emoji, no newline before it)
- ONE disease only — the most likely one
- If symptoms are too vague: Disease: Unclear symptoms
- NO medicine suggestions
- Keep entire response under 200 words"""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a plant pathologist. "
                        "Output ONLY structured diagnosis. "
                        "Never add extra text before or after the format. "
                        "The very first line MUST be: Disease: <name>"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        return _parse_disease_output(raw)

    except Exception as e:
        print(f"[ai_service] identify_disease error: {e}")
        return _DISEASE_FALLBACK.copy()


# ── Disease government support ─────────────────────────────────────────────────

def get_disease_support(crop: str, location: str, symptoms: str) -> str:
    prompt = f"""What government support, subsidies and schemes are available
for a {crop} farmer in {location} dealing with:

{symptoms}

Include:
- Crop insurance claims (PMFBY) for disease losses
- Free pesticide or medicine schemes
- KVK (Krishi Vigyan Kendra) support
- State agriculture department helplines
- Emergency crop loss compensation
- Any relevant helpline numbers

Be specific and practical. Keep response under 300 words."""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert on Indian agricultural government support for crop disease management.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ai_service] get_disease_support error: {e}")
        return "Sorry, couldn't fetch support information. Please contact your local KVK office."


# ── Weather advice ─────────────────────────────────────────────────────────────

def get_weather_advice(profile: dict, weather: dict) -> str:
    prompt = f"""Current weather for {weather['city']}:
- Temperature: {weather['temp']}°C (feels like {weather['feels_like']}°C)
- Humidity: {weather['humidity']}%
- Wind Speed: {weather['wind_speed']} m/s
- Condition: {weather['description']}
- Current Rain: {weather['rain']}mm

48-hour forecast:
{weather['forecast']}

Farmer details:
- Name: {profile['name']}
- Crop: {profile['crop']}
- Location: {profile['location']}

Based on this weather, give specific farming advice:

1. 🌱 CROP ACTIVITY TODAY
   - What to do / what to avoid

2. 💧 IRRIGATION ADVICE
   - Irrigate or not, how much

3. 🧪 SPRAYING ADVICE
   - Is it good weather to spray, best time

4. ⚠️ WEATHER WARNINGS
   - Risks and precautions

5. 📅 NEXT 2 DAYS PLAN
   - Key actions over next 48 hours

Keep advice practical and specific to {profile['crop']} crop. Under 350 words."""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert agricultural advisor giving precise farming advice based on weather for Indian farmers.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ai_service] get_weather_advice error: {e}")
        return "Sorry, couldn't generate weather advice. Please try again."


# ── RAG-grounded treatment ─────────────────────────────────────────────────────

def get_rag_treatment(
    crop: str,
    location: str,
    disease: str,
    rag_context: str,
) -> str:
    prompt = f"""A farmer in {location} grows {crop} and has been diagnosed with: {disease}.

The following treatment information was retrieved from official CIBRC/ICAR databases:

--- RETRIEVED CONTEXT ---
{rag_context}
--- END CONTEXT ---

Using ONLY the above context (do not invent medicines not listed), write a short,
practical treatment message for the farmer. Format:

💊 Recommended Treatment:
• <medicine name> — <formulation> — <dosage>
• (second option if available)

⏳ Waiting period: <days before harvest>
💧 Water: <dilution>

⚠️ Always confirm with local agriculture officer or KVK before spraying.

Keep entire response under 200 words. Use simple English."""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an agricultural advisor. "
                        "Use ONLY the provided context to give treatment advice. "
                        "Never invent medicines not mentioned in the context. "
                        "Always add a disclaimer to verify with local experts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ai_service] get_rag_treatment error: {e}")
        return (
            "⚠️ Could not generate RAG-grounded treatment advice.\n"
            "Please contact your local KVK or agriculture officer for guidance."
        )


# ── AI fallback treatment ──────────────────────────────────────────────────────

def get_ai_fallback_treatment(crop: str, location: str, disease: str) -> str:
    prompt = f"""A farmer in {location} has {disease} in their {crop} crop.
The verified medicine database had no entry for this.

Provide general fallback guidance in this exact format:

Common Treatments:
• <pesticide/fungicide name> — <brief usage note>
• <alternative option>

General Dosage Note:
<one sentence on typical dosage caution>

Precautions:
• <point 1>
• <point 2>

⚠️ This is general guidance only. Confirm with local agriculture officer or KVK before spraying.

Keep entire response under 150 words."""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an agricultural expert giving fallback treatment advice. "
                        "Always include a disclaimer to verify with local experts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=250,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ai_service] get_ai_fallback_treatment error: {e}")
        return (
            "⚠️ Could not generate treatment advice.\n"
            "Please contact your local KVK or agriculture officer for guidance."
        )