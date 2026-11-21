import logging
import time
from functools import lru_cache
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import BaseCallbackHandler
from app.core.config import settings

log = logging.getLogger(__name__)


class QuotaExceeded(RuntimeError):
    pass


class Usage(BaseCallbackHandler):
    def on_llm_end(self, response, **kwargs):
        for batch in response.generations:
            for generation in batch:
                usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
                if usage:
                    log.info("llm_tokens=%s", {key: usage.get(key) for key in ("input_tokens", "output_tokens")})


@lru_cache(maxsize=32)
def get_llm(role="default", temperature=None):
    model = settings.name_for(role)
    provider = settings.LLM_PROVIDER
    if ":" in model:
        provider, model = model.split(":", 1)
    return init_chat_model(model=model, model_provider=provider,
                           temperature=temperature if temperature is not None else (0 if role == "router" else settings.LLM_TEMPERATURE),
                           timeout=settings.LLM_TIMEOUT, max_retries=0, callbacks=[Usage()],
                           **settings.credentials(provider))


def invoke(runnable, messages, role="default"):
    for attempt in range(settings.LLM_MAX_RETRIES + 1):
        start = time.monotonic()
        try:
            return runnable.invoke(messages)
        except Exception as exc:
            code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if str(code) != "429" and not any(marker in str(exc).lower() for marker in ("429", "resource_exhausted", "rate limit")):
                raise
            if attempt == settings.LLM_MAX_RETRIES:
                raise QuotaExceeded("Model temporarily rate limited") from None
            time.sleep(min(2 ** attempt, 8))
        finally:
            log.info("llm_model=%s role=%s latency_ms=%d", settings.name_for(role), role, (time.monotonic()-start)*1000)
