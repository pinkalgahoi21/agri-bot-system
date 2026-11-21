from datetime import date
from urllib.parse import urlsplit
import logging


def live_schemes(crop, location, topic="agricultural schemes"):
    from ddgs import DDGS
    query = f"site:gov.in {topic[:150]} agriculture {crop} {location} {date.today().year}"
    for attempt in range(2):
        try:
            rows = DDGS(timeout=6).text(query, backend="duckduckgo", max_results=6)
            results = []
            for row in rows:
                link = row.get("href", "")
                parts = urlsplit(link)
                if parts.scheme == "https" and (parts.hostname or "").endswith(".gov.in"):
                    results.append(f"{row.get('title', '')}: {row.get('body', '')[:500]} {link}")
            if results:
                return "\n".join(results)
        except Exception:
            logging.getLogger(__name__).warning("Scheme search unavailable (attempt %d)", attempt + 1)
    return "Live search unavailable or no official matches. " + search_schemes(crop, location)


def search_schemes(crop, location):
    return (f"For a {crop} farmer in {location}, use myScheme to filter central and state schemes: "
            "https://www.myscheme.gov.in/ . For crop insurance check PMFBY: https://pmfby.gov.in/ . "
            "These are discovery resources, not a live eligibility check. Do not invent deadlines, amounts or eligibility.")
