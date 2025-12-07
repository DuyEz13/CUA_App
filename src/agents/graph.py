from langgraph.graph import StateGraph, END
from agents.planner_state import PlannerState
from agents.planner import Planner
import pyautogui
import base64
import io
from typing import Dict, List, Tuple
from tools.computer_use.AgentS.runner import run_computer_use_with_query
from utils.common_utils import parse_last_step
import json
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
import uuid

class PlannerGraph:
    def __init__(self, engine_params: Dict):
        self.llm = Planner(engine_params)
        self.checkpointer = InMemorySaver()
        self.graph = self.build_graph()

    # ------------------- NODES ----------------------

    def node_make_plan(self, state: PlannerState):
        plan_text = self.llm.plan_predict(state.query)
        return {
            "steps": plan_text,
            "current_step": 0,
            "cua_result": None,
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
            verify_result = self.llm.verify_predict(cua_result_str)
            if (verify_result[0] == 'A'):
                reason = verify_result[2:]
                human_approved = interrupt(reason)
                return {
                    "approved": False,
                    "human_approved": human_approved,  
                    "interrupt_reason": reason
                }
            else:
                state.current_step = state.current_step - 1

        return {
            "decision": "CONTINUE",
        }

    # ------------------- CONDITIONAL EDGES ----------------------

    def route_after_verify(self, state: PlannerState):
        if state.decision == "END":
            return "end"
        return "continue"

    # ------------------- CUA TOOL EXECUTION ----------------------

    def node_cua_execute(self, state: PlannerState):
        step = state.refined_step or state.steps[state.current_step]
        print("-" * 60)
        print(step)
        print("-" * 60)
        step = "Only do the following instruction. Do not do anything beside it. " + step
        response = run_computer_use_with_query(step)
        cua_result = parse_last_step(response)
        print(response)
        return {
            "step_result": step,
            "current_step": state.current_step + 1,
            "response": response,
            "cua_result": cua_result,
        }

    # ------------------- BUILD GRAPH ----------------------

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
