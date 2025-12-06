from core.module import BaseModule
from prompt.prompt import PROMPT

class Worker(BaseModule):
    def __init__(self, model, api_key):
        super().__init__(model, api_key)
        self.reset()

    def reset(self):
        self.agent, _ = self._create_agent(system_prompt=PROMPT.PLANNING, api_key=self.api_key)
        _, self.v_agent = self._create_agent(system_prompt=PROMPT.VERIFING, api_key=self.api_key)

    def plan_from_query(self, query: str):
        response = self.agent.invoke({
            "messages": [{"role":"user", "content": query}]
        })
        return response["messages"][1].content
    
    def verify_screen(self, step: str, screenshot_base64):
        # response = self.v_agent.invoke({
        #     "messages": [{"role": "user", "content": [
        #             {"type": "text", "text": f"Step: {step}"},
        #             {
        #                 "type": "image",
        #                 "image_url": f"data:image/png;base64,{screenshot_base64}"
        #     }]}]
        # })
        # return response
        messages = [
            {"role": "system", "content": "Bạn là verify agent."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Step: {step}"},
                    {
                        "type": "image",
                        "image_url": f"data:image/png;base64,{screenshot_base64}"
                    }
                ]
            }
        ]

        return self.v_agent.invoke(messages)

    # def evaluate_step(self, step: str, observation) -> str:
    #     system_prompt = """
    #     You are an evaluator.
    #     """
    #     user_prompt = f"""
    #     Step: {step}
    #     Observation: {observation}
    #     """
    #     return self.llm.chat_completion(
    #         system=system_prompt,
    #         user=user_prompt,
    #     ).text