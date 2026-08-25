"""
services/language_service.py
Language detection, multilingual AI response, and TTS language resolution.

Internal convention: all language keys are FULL NAMES ("hindi", "urdu").
Whisper returns ISO codes ("hi", "ur") — use normalize_language() to convert.
"""
import google.generativeai as genai
from config import GOOGLE_API_KEY, AI_MODEL

genai.configure(api_key=GOOGLE_API_KEY)


# ── Language registry ──────────────────────────────────────────────────────────
# Canonical keys are full names — used throughout LANGUAGE_INSTRUCTIONS,
# get_language_display_name(), and _resolve_gtts_lang() in voice_service.py.

SUPPORTED_LANGUAGES: dict[str, str] = {
    # Major scheduled languages
    "english":        "en",
    "hindi":          "hi",
    "tamil":          "ta",
    "telugu":         "te",
    "kannada":        "kn",
    "malayalam":      "ml",
    "bengali":        "bn",
    "marathi":        "mr",
    "gujarati":       "gu",
    "punjabi":        "pa",
    "odia":           "or",
    "assamese":       "as",
    "urdu":           "ur",
    "sanskrit":       "sa",
    "konkani":        "kok",
    "manipuri":       "mni",
    "nepali":         "ne",
    "sindhi":         "sd",
    "bodo":           "brx",
    "dogri":          "doi",
    "kashmiri":       "ks",
    "maithili":       "mai",
    "santali":        "sat",
    # Regional dialects
    "bhojpuri":       "bho",
    "rajasthani":     "raj",
    "haryanvi":       "bgc",
    "chhattisgarhi":  "hne",
    "magahi":         "mag",
    "tulu":           "tcy",
    "coorg":          "kfa",
    "gondi":          "gon",
    "mundari":        "unr",
    "kurukh":         "kru",
    "ho":             "hoc",
    "khasi":          "kha",
    "mizo":           "lus",
    "nagamese":       "nag",
    "kokborok":       "trp",
}

# Reverse map: ISO code → full name
# Used by normalize_language() to convert Whisper output ("hi") → "hindi"
_ISO_TO_NAME: dict[str, str] = {iso: name for name, iso in SUPPORTED_LANGUAGES.items()}

# Additional ISO aliases Whisper may produce that aren't 1:1 in the map above
_ISO_TO_NAME.update({
    "zh":  "english",   # Chinese → fallback
    "ar":  "urdu",      # Arabic script → closest supported
    "fa":  "urdu",      # Farsi → closest supported
})


def normalize_language(lang: str) -> str:
    """
    Convert any language identifier to the canonical full name used
    throughout this module.

    Accepts:
        ISO codes  : "hi" → "hindi",  "ta" → "tamil",  "ur" → "urdu"
        Full names : "hindi" → "hindi"  (passthrough)
        Unknown    : anything not found → "english"

    This is the bridge between Whisper (returns ISO) and the rest of
    the system (keyed on full names). Always call this before passing
    a language value to get_language_display_name(), LANGUAGE_INSTRUCTIONS,
    or get_multilingual_response().
    """
    if not lang:
        return "english"
    lang = lang.strip().lower()
    # Already a full name
    if lang in SUPPORTED_LANGUAGES:
        return lang
    # ISO code → full name
    if lang in _ISO_TO_NAME:
        return _ISO_TO_NAME[lang]
    return "english"


# ── Language instructions ──────────────────────────────────────────────────────

LANGUAGE_INSTRUCTIONS: dict[str, str] = {
    "english":        "Reply in simple English.",
    "hindi":          "हिंदी में सरल भाषा में जवाब दें। (Reply in simple Hindi, Devanagari script)",
    "tamil":          "தமிழில் எளிமையான மொழியில் பதில் கூறுங்கள். (Reply in simple Tamil)",
    "telugu":         "సరళమైన తెలుగులో సమాధానం ఇవ్వండి. (Reply in simple Telugu)",
    "kannada":        "ಸರಳ ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ. (Reply in simple Kannada)",
    "malayalam":      "ലളിതമായ മലയാളത്തിൽ മറുപടി നൽകുക. (Reply in simple Malayalam)",
    "bengali":        "সহজ বাংলায় উত্তর দিন। (Reply in simple Bengali)",
    "marathi":        "सोप्या मराठीत उत्तर द्या. (Reply in simple Marathi)",
    "gujarati":       "સરળ ગુજરાતીમાં જવાબ આપો. (Reply in simple Gujarati)",
    "punjabi":        "ਸਰਲ ਪੰਜਾਬੀ ਵਿੱਚ ਜਵਾਬ ਦਿਓ. (Reply in simple Punjabi, Gurmukhi script)",
    "odia":           "ସରଳ ଓଡ଼ିଆରେ ଉତ୍ତର ଦିଅନ୍ତୁ। (Reply in simple Odia)",
    "assamese":       "সহজ অসমীয়াত উত্তৰ দিয়ক। (Reply in simple Assamese)",
    "urdu":           "آسان اردو میں جواب دیں۔ (Reply in simple Urdu, Nastaliq script)",
    "sanskrit":       "सरलसंस्कृतेन उत्तरं ददातु। (Reply in simple Sanskrit)",
    "konkani":        "Reply in simple Konkani language.",
    "manipuri":       "Reply in simple Manipuri (Meitei script).",
    "nepali":         "सरल नेपालीमा जवाफ दिनुहोस्। (Reply in simple Nepali)",
    "sindhi":         "Reply in simple Sindhi language.",
    "bodo":           "Reply in simple Bodo language.",
    "dogri":          "Reply in simple Dogri language.",
    "kashmiri":       "Reply in simple Kashmiri language.",
    "maithili":       "सरल मैथिलीमे उत्तर दिअ। (Reply in simple Maithili)",
    "santali":        "Reply in simple Santali language.",
    "bhojpuri":       "सरल भोजपुरी में जवाब दीं। (Reply in simple Bhojpuri)",
    "rajasthani":     "सरल राजस्थानी में जवाब दो। (Reply in simple Rajasthani)",
    "haryanvi":       "सरल हरियाणवी में जवाब दो। (Reply in simple Haryanvi)",
    "chhattisgarhi":  "सरल छत्तीसगढ़ी में जवाब दव। (Reply in simple Chhattisgarhi)",
    "magahi":         "सरल मगही में जवाब दीं। (Reply in simple Magahi)",
    "tulu":           "Reply in simple Tulu language.",
    "coorg":          "Reply in simple Kodava/Coorg language.",
    "gondi":          "Reply in simple Gondi language.",
    "mundari":        "Reply in simple Mundari language.",
    "kurukh":         "Reply in simple Kurukh language.",
    "ho":             "Reply in simple Ho language.",
    "khasi":          "Reply in simple Khasi language.",
    "mizo":           "Reply in simple Mizo language.",
    "nagamese":       "Reply in simple Nagamese language.",
    "kokborok":       "Reply in simple Kokborok language.",
}


# ── Display names ──────────────────────────────────────────────────────────────

_DISPLAY_NAMES: dict[str, str] = {
    "english":       "English 🇬🇧",
    "hindi":         "Hindi / हिंदी",
    "tamil":         "Tamil / தமிழ்",
    "telugu":        "Telugu / తెలుగు",
    "kannada":       "Kannada / ಕನ್ನಡ",
    "malayalam":     "Malayalam / മലയാളം",
    "bengali":       "Bengali / বাংলা",
    "marathi":       "Marathi / मराठी",
    "gujarati":      "Gujarati / ગુજરાતી",
    "punjabi":       "Punjabi / ਪੰਜਾਬੀ",
    "odia":          "Odia / ଓଡ଼ିଆ",
    "assamese":      "Assamese / অসমীয়া",
    "urdu":          "Urdu / اردو",
    "bhojpuri":      "Bhojpuri / भोजपुरी",
    "rajasthani":    "Rajasthani / राजस्थानी",
    "haryanvi":      "Haryanvi / हरियाणवी",
    "chhattisgarhi": "Chhattisgarhi / छत्तीसगढ़ी",
    "maithili":      "Maithili / मैथिली",
    "konkani":       "Konkani / कोंकणी",
    "nepali":        "Nepali / नेपाली",
    "kashmiri":      "Kashmiri / कश्मीरी",
    "dogri":         "Dogri / डोगरी",
    "manipuri":      "Manipuri / মৈতৈলোন্",
    "sindhi":        "Sindhi / سنڌي",
    "sanskrit":      "Sanskrit / संस्कृत",
    "tulu":          "Tulu / ತುಳು",
    "khasi":         "Khasi",
    "mizo":          "Mizo",
    "bodo":          "Bodo / बड़ो",
    "santali":       "Santali / ᱥᱟᱱᱛᱟᱲᱤ",
    "gondi":         "Gondi / गोंडी",
    "magahi":        "Magahi / मगही",
    "mundari":       "Mundari",
    "kurukh":        "Kurukh",
    "nagamese":      "Nagamese",
    "kokborok":      "Kokborok",
    "ho":            "Ho",
    "coorg":         "Kodava / Coorg",
}


def get_language_display_name(language: str) -> str:
    """
    Return a human-readable display name for a language identifier.
    Accepts both ISO codes ("hi") and full names ("hindi").
    Always returns a clean name — never a raw ISO code.

    "hi"    → "Hindi / हिंदी"   (was returning "Hi" before — BUG FIXED)
    "ur"    → "Urdu / اردو"     (was returning "Ur" before — BUG FIXED)
    "hindi" → "Hindi / हिंदी"   (full name passthrough)
    """
    name = normalize_language(language)   # ISO → full name first
    return _DISPLAY_NAMES.get(name, "English 🇬🇧")


# ── Language detection ─────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """
    Detect which Indian language the farmer is writing in.
    Returns a full language name ("hindi", "urdu") — NOT an ISO code.
    Falls back to "english" on any failure.
    """
    language_list = ", ".join(SUPPORTED_LANGUAGES.keys())
    prompt = f"""Detect the language of this text: "{text}"

Choose ONLY from this list:
{language_list}

Rules:
- If it looks like Hindi but informal/dialectal from UP/Bihar → bhojpuri or magahi
- If from Rajasthan informal → rajasthani
- If from Haryana informal → haryanvi
- If unsure → english

Reply with ONLY one word from the list above."""

    try:
        model = genai.GenerativeModel(
            model_name=AI_MODEL,
            system_instruction="You are an expert Indian language detector. Reply with only one word.",
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=10,
            ),
        )
        response = model.generate_content(prompt)
        detected = (
            response.text
            .strip().lower()
            .replace(".", "").replace(",", "")
        )
        if detected not in SUPPORTED_LANGUAGES:
            print(f"[language] Unknown detection result: '{detected}' — defaulting to english")
            return "english"
        return detected

    except Exception as e:
        print(f"[language] detect_language error: {e}")
        return "english"


# ── Multilingual AI response ───────────────────────────────────────────────────

def get_multilingual_response(
    user_message: str,
    language: str,
    profile: dict,
    history: list,
) -> str:
    """
    Get an AI farming response in the farmer's own language.
    Normalises language first — accepts both ISO codes and full names.
    Never suggests specific pesticide or medicine brand names.
    """
    lang_name   = normalize_language(language)
    instruction = LANGUAGE_INSTRUCTIONS.get(lang_name, "Reply in simple English.")

    system_prompt = f"""You are an expert agricultural advisor for Indian farmers.

Farmer details:
- Name: {profile['name']}
- Location: {profile['location']}
- Main crop: {profile['crop']}

CRITICAL LANGUAGE RULE: {instruction}
You MUST reply in the detected language only.
Do NOT mix languages unless the farmer mixes them.

Give practical advice about:
- Crops, fertilizers, soil health, irrigation
- Pest and disease identification (symptoms, causes, prevention only)
- Weather-based farming advice
- Government schemes for farmers

STRICT RULES — follow ALL without exception:
1. NEVER mention ANY pesticide, fungicide, or medicine name whatsoever.
   This includes ALL chemical names such as:
   Mancozeb, Carbendazim, Copper Oxychloride, Copper Hydroxide,
   Chlorpyrifos, Thiram, Metalaxyl, Imidacloprid, or ANY other.
   Not even as an example. Not even in passing.
2. For ANY disease/pest/treatment question say ONLY (in farmer's language):
   "Please use the /disease command for verified medicine recommendations
   from the official CIBRC database with correct dosage."
3. You MAY suggest general prevention only:
   removing infected leaves, improving drainage, avoiding waterlogging,
   crop rotation, using certified seeds.
4. You MAY name fertilizer types: urea, DAP, potash — NOT pesticides.
5. Keep answers under 250 words.
6. If asked anything unrelated to farming, politely decline
   in the farmer's language."""

    # Build conversation context string for Gemini
    history_text = ""
    for msg in history:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        history_text += f"{role}: {content}\n"
    full_user = (history_text + f"User: {user_message}").strip()

    try:
        model = genai.GenerativeModel(
            model_name=AI_MODEL,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,    # ← lowered from 0.4 — stricter rule following
                max_output_tokens=500,     # ← reduced from 600 — shorter = less drift
            ),
        )
        response = model.generate_content(full_user)
        return response.text

    except Exception as e:
        print(f"[language] get_multilingual_response error: {e}")
        return "Sorry, I couldn't process your request. Please try again."