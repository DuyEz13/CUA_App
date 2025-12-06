from agents.worker import Worker
from typing import Dict, List, Tuple
import re

class Planner:
    def __init__(self,
                 engine_params: Dict):
        self.engine_params= engine_params
        self.full_step = []

        self.reset()

    def reset(self) -> None:
        self.executor = Worker(self.engine_params)

    def plan_predict(self, query: str):
        self.full_plan = self.executor.plan_from_query(query)
        for part in self.full_plan.split("Step "):
            part = part.strip()
            if part and part[0].isdigit():
                step_text = step_text = re.sub(r"^\d+\.\s*", "", part)
                self.full_step.append(step_text)
        return self.full_step
    
    def verify_predict(self, query):
        self.verify_cua_result = self.executor.verify_cua_result(query)
        return self.verify_cua_result