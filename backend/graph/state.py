from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class FarmerState(TypedDict, total=False):
    assessment: dict | None
    request: str | dict
    previous: str
    image: bool
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_id: int
    name: str
    location: str
    crop: str
