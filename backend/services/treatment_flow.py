import json
import logging

from services.ai_service import _chat
from services.advisory import pack
from services.vector_rag import search_pdf, table_page

WARNING = "AI-generated advice only. This treatment is not officially verified."


def assess(message, crop, image=False):
    raw = _chat(
        "Classify only the current request; prior farm notes are context, not evidence of farming intent. "
        "Return only JSON with kind (disease, farm, or unrelated). Farm includes growing from scratch, "
        "crop planning, soil suitability, agricultural schemes and weather. For unrelated requests give "
        "only a brief farming-only refusal in the user's language in summary. Also return "
        "crop and disease (common English retrieval terms), language (language of the request), "
        "and summary (brief tentative assessment in that language). Symptoms, pests and treatment "
        "questions are disease requests; schemes and weather are farm requests. If the issue is uncertain "
        "or not a plant, leave disease empty. Do not prescribe. For image assessments respect "
        "the supplied confidence: low confidence means leave disease empty.",
        json.dumps({"request": message, "profile_crop": crop, "image_assessment": image}, ensure_ascii=False),
    )
    item = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
    if not image and item.get("kind") not in ("farm", "disease"):
        refusal = item.get("summary") if item.get("kind") == "unrelated" else None
        return {**pack("Agri-Bot", [{"heading": "", "body": refusal or "I can help with farming questions only."}]), "out_of_scope": True}
    if item["kind"] == "farm" and not image:
        return None
    summary = item["summary"]
    issue = item.get("disease", "").strip()
    plant = item.get("crop", "").strip()
    if not issue or not plant:
        return pack(summary, [{"heading": "Next step", "body": "Diagnosis uncertain. Provide clearer symptoms or consult a local agricultural adviser before treatment."}])
    try:
        hits = search_pdf(issue, plant)
        hits = [{"metadata": hit["metadata"], "document": table_page(hit["metadata"]["source"], hit["metadata"]["page"])} for hit in hits]
    except Exception:
        logging.getLogger(__name__).warning("PDF search unavailable", exc_info=True)
        hits = []
    context = json.dumps({"crop": plant, "disease": issue, "language": item["language"], "passages": hits}, ensure_ascii=False)
    if hits:
        raw = _chat("Use only a passage that explicitly links the crop, disease and treatment in the same entry. "
                    "Use the product heading ABOVE the matching row, never a heading below it. If the heading "
                    "is on a previous page, skip that entry. Do not give doses. Return JSON with index (zero-based passage number), "
                    "quote (verbatim supporting text) and advice (brief summary in requested language). "
                    "If evidence is insufficient return {}. Do not invent application instructions.", context)
        try:
            evidence = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            number = evidence['index']
            if type(number) is int and 0 <= number < len(hits):
                hit = hits[number]
                quote = evidence['quote'].strip()
                if quote and " ".join(quote.split()) in " ".join(hit['document'].split()) and evidence['advice'].strip():
                    source = hit['metadata']
                    return pack(summary, [{"heading": "Reference-based advice", "body": evidence['advice']},
                                          {"heading": "Source", "body": f"{source['source']}, p. {source['page']}\n{quote}"}])
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
    advice = _chat("Give brief conservative nonchemical crop care steps for this suspected issue, in the "
                   "requested language. Do not promise a cure, suggest pesticide products or doses, "
                   "or claim official verification. Recommend local confirmation.", json.dumps({"crop": plant, "issue": issue, "language": item["language"]}))
    return pack(summary, [{"heading": "Suggested care", "body": advice.strip()},
                          {"heading": "Verification notice", "body": WARNING}], True)
