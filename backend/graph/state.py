from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class FarmerState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_id: int
    name: str
    location: str
    crop: str
