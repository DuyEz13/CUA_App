from core.module import BaseModule
from prompt.prompt import PROMPT
from utils.common_utils import call_llm_safe

class Worker(BaseModule):
    def __init__(self, engine_params):
        super().__init__(engine_params)
        self.reset()

    def reset(self):
        self.agent = self._create_agent(system_prompt=PROMPT.PLANNING)
        self.v_agent = self._create_agent_lang(system_prompt=PROMPT.VERIFING)

    def plan_from_query(self, query: str):
        self.agent.add_message(text_content=query, role="user")
        full_plan = call_llm_safe(
            self.agent,
        )
        return full_plan
    
    def verify_cua_result(self, query: str):
        response = self.v_agent.invoke(
            {
                "messages": [{"role": "user", "content": query}]
            }
        )
        signal = response['messages'][1].content[0]['text']
        return signal