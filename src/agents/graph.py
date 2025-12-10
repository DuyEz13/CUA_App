from langgraph.graph import StateGraph, END
from agents.planner_state import PlannerState
from agents.planner import Planner
import pyautogui
import base64
import io
from typing import Dict, List, Tuple, Any
from tools.computer_use.AgentS.runner import run_computer_use_with_query
from utils.common_utils import parse_last_step, parse_token_usage, write_token_log_txt
import json
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
import uuid
import os
import logging
from agents.token_tracker import TokenUsageLogger

BASE_PATH = r'E:\test\CUA_App\src\token_log'
task_id = str(uuid.uuid4())
task_path = os.path.join(BASE_PATH, task_id)
os.makedirs(task_path, exist_ok=True)

token_logger = TokenUsageLogger(log_dir=task_path)

def _track_graph_node_tokens(step: int, response_data: Any = None, model_name: str = "", agent_name: str = ""):
    usage = response_data.usage
    print(usage)
    token_logger.log_usage(
        model=model_name,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        context=f"{agent_name} Step {step}",
        metadata={"step": step, "agent": agent_name}
    )

class PlannerGraph:
    def __init__(self, engine_params: Dict):
        self.llm = Planner(engine_params)
        self.checkpointer = InMemorySaver()
        self.graph = self.build_graph()
        self.engine_params = engine_params

    # NODES

    def node_make_plan(self, state: PlannerState):
        plan_text, full_rp = self.llm.plan_predict(state.query)
        _track_graph_node_tokens(state.current_step, full_rp, self.engine_params['model'], "Planning Agent")
        return {
            "steps": plan_text,
            "current_step": 0,
            "cua_result": None,
            "fail_reason_list": [],
        }

    def node_verify(self, state: PlannerState):
        if state.human_approved is True:
            if state.current_step == len(state.steps):
                return {
                    "approved": True,
                    "decision": "END",
                    "human_approved": None
                }
            else:                
                return {
                    "approved": True,
                    "decision": "CONTINUE",
                    "human_approved": None
                }

        if state.current_step == len(state.steps):
            return {"decision": "END"}
        

        if state.cua_result is not None and state.cua_result["signal"] == "Fail":
            cua_result_str = json.dumps(state.cua_result, ensure_ascii=False)
            verify_result, full_rp = self.llm.verify_predict(cua_result_str)
            _track_graph_node_tokens(state.current_step, full_rp, self.engine_params['model'], "Verifying Agent")
            reason = verify_result[2:]
            frl = state.fail_reason_list.append(reason)
            if (verify_result[0] == 'A'):
                #reason = verify_result[2:]
                human_approved = interrupt(reason)
                return {
                    "approved": False,
                    "human_approved": human_approved,  
                    "interrupt_reason": reason,
                    "fail_reason_list": frl
                }
            else:
                return{
                    'current_step': state.current_step - 1,
                    "fail_reason_list": frl
                }
                #state.current_step = state.current_step - 1

        return {
            "decision": "CONTINUE",
        }

    # CONDITIONAL EDGES

    def route_after_verify(self, state: PlannerState):
        if state.decision == "END":
            return "end"
        return "continue"

    # CUA EXECUTION

    def node_cua_execute(self, state: PlannerState):
        step = state.refined_step or state.steps[state.current_step]
        print("-" * 60)
        print(step)
        print("-" * 60)
        step = "Only do the following instruction. Do not do anything beside it. " + step
        response = run_computer_use_with_query(step)
        filename = f"cua_step_{state.current_step + 1}.txt"
        file_path = os.path.join(task_path, filename)
        print(file_path)
        cua_result = parse_last_step(response)
        if len(state.fail_reason_list) != 0:
            cua_result['fail_reason_list'] = state.fail_reason_list
        token_log = parse_token_usage(response)
        write_token_log_txt(token_log, file_path)
        print(response)
        return {
            "step_result": step,
            "current_step": state.current_step + 1,
            "response": response,
            "cua_result": cua_result,
        }

    def build_graph(self):
        g = StateGraph(PlannerState)

        g.add_node("make_plan", self.node_make_plan)
        g.add_node("verify", self.node_verify)
        g.add_node("cua_execute", self.node_cua_execute)


        g.set_entry_point("make_plan")

        g.add_edge("make_plan", "verify")

        # branching
        g.add_conditional_edges(
            "verify",
            self.route_after_verify,
            {
                "continue": "cua_execute",
                "end": END,
            }
        )

        g.add_edge("cua_execute", "verify")

        return g.compile(checkpointer=self.checkpointer)

    def run(self, query: str):
        initial = PlannerState(query=query)
        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
            }
        }
        state = self.graph.invoke(initial, config)

        return state
