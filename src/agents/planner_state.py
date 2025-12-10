from typing import List, Optional, Dict
from pydantic import BaseModel

class PlannerState(BaseModel):
    query: str
    steps: List[str] = []
    current_step: int = 0

    step_result: Optional[str] = None
    decision: Optional[str] = None

    refined_step: Optional[str] = None
    cua_result: Optional[Dict] = None

    human_approved: Optional[bool] = None      
    interrupt_reason: Optional[str] = None      
    approved: Optional[bool] = None

    fail_reason_list: Optional[List] = None 