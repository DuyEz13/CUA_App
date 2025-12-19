from core.module import BaseModule
from prompt.prompt import PROMPT
from utils.common_utils import call_llm_safe

class Worker(BaseModule):
    def __init__(self, engine_params):
        super().__init__(engine_params)
        self.reset()

    def reset(self):
        self.agent = self._create_agent(system_prompt=PROMPT.PLANNING)
        #self.v_agent = self._create_agent_lang(system_prompt=PROMPT.VERIFING)
        self.v_agent = self._create_agent(system_prompt=PROMPT.VERIFING)
        self.v_s_agent = self._create_agent(system_prompt=PROMPT.STEP_VERIFYING)
        self.pdf_agent = self._create_agent(system_prompt=PROMPT.PDF_EXTRACTOR)

    def plan_from_query(self, query: str):
        self.agent.add_message(text_content=query, role="user")
        full_plan, full_rp = call_llm_safe(
            agent=self.agent,
            temperature=None
        )
        return full_plan, full_rp
    
    def verify_step(self, query: str):
        self.v_s_agent.add_message(text_content=query, role="user")
        signal, _ = call_llm_safe(
            agent=self.v_s_agent,
            temperature=None
        )
        return signal
    
    def verify_cua_result(self, query: str):
        # response = self.v_agent.invoke(
        #     {
        #         "messages": [{"role": "user", "content": query}]
        #     }
        # )
        # try:
        #     signal = response['messages'][1].content[0]['text']
        # except:
        #     signal = response['messages'][1].content
        # return signal

        self.v_agent.add_message(text_content=query, role="user")
        signal, full_rp = call_llm_safe(
            agent=self.v_agent,
            temperature=None
        )
        return signal, full_rp
    
    def pdf_extract(self, img, query: str):
        self.pdf_agent.add_message(text_content=query, image_content=img, role="user")
        result, _ = call_llm_safe(
            agent=self.pdf_agent,
            temperature=None
        )
        return result
