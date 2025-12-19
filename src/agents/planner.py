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
        self.full_plan, full_rp = self.executor.plan_from_query(query)
        # for part in self.full_plan.split("Step "):
        #     part = part.strip()
        #     if part and part[0].isdigit():
        #         step_text = step_text = re.sub(r"^\d+\.\s*", "", part)
        #         self.full_step.append(step_text)
        header_re = re.compile(
            r"(?:(?<=^)|(?<=\n)|(?<=[\.\:\;\?\!\"'\)\(]))\s*Step\s+(\d+)\.\s*", re.DOTALL
        )

        matches = list(header_re.finditer(self.full_plan))

        if matches:
            for i, m in enumerate(matches):
                start = m.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(self.full_plan)
                #step_num = int(m.group(1))
                step_text = self.full_plan[start:end].strip()
                self.full_step.append(step_text)

        return self.full_step, full_rp
    
    def step_verify_predict(self, step):
        return self.executor.verify_step(step)
    
    def verify_predict(self, query):
        self.verify_cua_result, full_rp = self.executor.verify_cua_result(query)
        return self.verify_cua_result, full_rp
    
    def pdf_extract(self, query, img):
        return self.executor.pdf_extract(query=query, img=img)