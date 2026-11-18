import json
import re
from services.search_service import search_schemes


def pack(title, sections, fallback=False):
    report = {'title': title, 'sections': sections}
    text = '\n\n'.join([title] + [part['heading'] + '\n' + part['body'] for part in sections])
    return {'advisory': report, 'response': text, 'fallback': fallback}


def parse_answer(content):
    if isinstance(content, list):
        content = ''.join(item if isinstance(item, str) else item.get('text', '') for item in content if isinstance(item, (str, dict)))
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip(), flags=re.I)
    try:
        report = json.loads(raw)
        title, sections = report['title'], report['sections']
        if isinstance(title, str) and title.strip() and isinstance(sections, list) and sections and all(isinstance(item, dict) and all(isinstance(item.get(key), str) and item[key].strip() for key in ('heading', 'body')) for item in sections):
            return pack(title, sections)
    except (TypeError, KeyError, ValueError):
        pass
    if raw and not raw.startswith(('{', '[')):
        return pack('Field advice', [{'heading': 'Response', 'body': raw}])
    raise ValueError('Missing structured model reply')


def symptom_question(message, crop):
    if not re.search(r'\b(meri|mere|mera|fasal|paudha|paudhe|hai|hain)\b', message, re.I):
        return None
    if not re.search(r'\b(black|kaal[aei]|kal[aei]|yellow|peel[aei]|brown)\b', message, re.I):
        return None
    if re.search(r'\b(patt\w*|leaf|leaves|stem|fruit|phal|tana|tane|jad|root|blight|rot|spot\w*|dhab\w*)\b', message, re.I):
        return None
    named = re.search(r'\b(tomato|tamatar|wheat|gehun|rice|dhan|potato|aloo|cotton|kapas|maize|makka|onion|pyaz)\b', message, re.I)
    plant = named.group() if named else crop
    return pack(f"{plant}: rang kahan badla hai?", [{"heading": "Thoda aur batayein",
        "body": "Pattiyon, tane ya phal par rang badla hai? Ek close-up photo bhej sakte hain? Sirf rang se bimari pakki nahi hoti."}])


def offline_answer(message, crop, location):
    schemes = re.search(r'scheme|subsid|insurance|योजना|सब्सिडी|बीमा', message, re.I)
    hindi = bool(re.search('[ऀ-ॿ]', message))
    if schemes:
        body = ('अपने राज्य और पात्रता के लिए https://www.myscheme.gov.in/ देखें। फसल बीमा: https://pmfby.gov.in/' if hindi else search_schemes(crop, location))
    else:
        body = ('अभी जांच उपलब्ध नहीं है। फसल की साफ तस्वीर और लक्षण भेजें या स्थानीय कृषि केंद्र से संपर्क करें।' if hindi else 'I could not assess this request. Try again with a clear crop photo and symptoms, or contact your local agricultural extension office.')
    return pack('सेवा सीमित है' if hindi else 'Live advice unavailable', [{'heading': 'अगला कदम' if hindi else 'Next step', 'body': body}], True)
