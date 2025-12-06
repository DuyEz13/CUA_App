from typing import List, Optional
from pydantic import BaseModel

class PlannerState(BaseModel):
    query: str
    steps: List[str] = []
    current_step: int = 0

    step_result: Optional[str] = None
    decision: Optional[str] = None

    refined_step: Optional[str] = None