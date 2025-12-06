from agents.worker import Worker

class Planner:
    def __init__(self, 
                 model: str,
                 api_key: str):
        self.model = model
        self.api_key = api_key
        self.full_step = []

        self.reset()

    def reset(self) -> None:
        self.executor = Worker(self.model, self.api_key)

    def plan_predict(self, query: str):
        self.full_plan = self.executor.plan_from_query(query)
        for part in self.full_plan.split("Step "):
            part = part.strip()
            if part and part[0].isdigit():
                step_text = part.split(". ")[1]
                self.full_step.append(step_text)
        return self.full_step
    
    def verify_predict(self, step, screenshot_base64):
        self.screen_detail = self.executor.verify_screen(step, screenshot_base64)
        return self.screen_detail