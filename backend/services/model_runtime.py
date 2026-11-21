import base64
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import get_llm, invoke


def generate(system, prompt, *, role="default", temperature=None, max_tokens=600, media=None):
    content = prompt
    if media:
        kind, mime, payload = media
        encoded = base64.b64encode(payload).decode("ascii")
        block = {"type": kind, "base64": encoded, "mime_type": mime}
        if kind == "image":
            block = {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
        content = [{"type": "text", "text": prompt}, block]
    result = invoke(get_llm(role, temperature).bind(max_tokens=max_tokens), [SystemMessage(content=system), HumanMessage(content=content)], role)
    return result.text.strip()
