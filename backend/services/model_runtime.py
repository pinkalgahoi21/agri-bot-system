import base64
import os
from functools import lru_cache
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from config import AGENT_MODEL


@lru_cache(maxsize=12)
def model(spec=AGENT_MODEL, **options):
    provider, separator, name = spec.partition("/")
    return init_chat_model(name if separator else spec, model_provider=provider if separator else None,
                           timeout=float(os.getenv("MODEL_TIMEOUT_SECONDS", "45")), max_retries=1, **options)


def generate(system, prompt, *, spec=AGENT_MODEL, temperature=0.4, max_tokens=600, media=None):
    content = prompt
    if media:
        kind, mime, payload = media
        encoded = base64.b64encode(payload).decode("ascii")
        block = {"type": kind, "base64": encoded, "mime_type": mime}
        if kind == "image" and spec.startswith("groq/"):
            block = {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
        content = [{"type": "text", "text": prompt}, block]
    result = model(spec, temperature=temperature, max_tokens=max_tokens).invoke([SystemMessage(content=system), HumanMessage(content=content)])
    return result.text.strip()
