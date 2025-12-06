from core.mllm import LMMAgent
from typing import Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

class BaseModule:
    def __init__(self, engine_params: Dict):
        self.engine_params = engine_params

    # def _create_agent(self, api_key, system_prompt: str):
    #     model = ChatGoogleGenerativeAI(model=self.model, 
    #                                    temperature=0, 
    #                                    convert_system_message_to_human=True, 
    #                                    google_api_key=api_key)
    #     agent = create_agent(
    #         model=model,
    #         #tools=tools,
    #         system_prompt=system_prompt,
    #     )
    #     return agent, model
    def _create_agent(
        self, system_prompt: str = None, engine_params: Optional[Dict] = None
    ) -> LMMAgent:
        """Create a new LMMAgent instance"""
        agent = LMMAgent(engine_params or self.engine_params)
        if system_prompt:
            agent.add_system_prompt(system_prompt)
        return agent
    
    def _create_agent_lang(
            self, system_prompt: str = None, engine_params: Optional[Dict] = None
    ):
        if self.engine_params["engine_type"] == "gemini":
            model = ChatGoogleGenerativeAI(model=self.engine_params["model"], 
                                       temperature=0, 
                                       google_api_key=self.engine_params["api_key"])
            agent = create_agent(
                model=model,
                #tools=tools,
                system_prompt=system_prompt,
            )
        return agent