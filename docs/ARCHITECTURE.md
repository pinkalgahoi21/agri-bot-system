# Request flow

```mermaid
flowchart TD
  Web --> API
  Telegram --> API
  API --> Normalize[Text or voice transcript or validated photo]
  Normalize --> Context[Read profile and crop memory]
  Context --> Router[LangGraph intent_router: structured LLM decision]
  Router --> Clarify[Clarify or refuse]
  Router --> Disease[Identify issue and search Chroma]
  Disease --> Evidence[Check page and table evidence or use labelled fallback]
  Router --> Agent[Farm agent: answer directly or choose a tool]
  Agent --> Tools[OpenWeather or DuckDuckGo scheme search]
  Tools --> Agent
  Agent --> Answer
  Clarify --> Answer
  Evidence --> Answer
  Answer --> Memory[Update farm note]
  Memory --> Client[Text plus optional spoken reply]
```

The SQL farm note supplies cross-request continuity; it is not a LangGraph execution checkpoint. Unclear/mismatched photos stop at validation before treatment. Credential checks and upload limits are outside the model's control.
