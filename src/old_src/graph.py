from langgraph.graph import StateGraph, END
from agents.planner_state import PlannerState
from agents.planner import Planner
import pyautogui
import base64
from io import BytesIO

class PlannerGraph:
    def __init__(self, model: str, api_key: str):
        self.llm = Planner(model, api_key)
        self.graph = self.build_graph()

    # ------------------- NODES ----------------------

    def node_make_plan(self, state: PlannerState):
        plan_text = self.llm.plan_predict(state.query)
        #steps = [line.strip("-•0123456789. ") for line in plan_text.split("\n") if line.strip()]
        return {
            "steps": plan_text,
            "current_step": 0
        }

    def node_verify(self, state: PlannerState):
        step = state.refined_step or state.steps[state.current_step]
        obs = state.step_result or ""
        screenshot = pyautogui.screenshot()

    # convert to base64
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        screen_detail = self.llm.verify_predict(state.current_step, img_base64)
        print(screen_detail)

        #judgment = self.llm.verify(step, obs)

        # if "END" in judgment.upper():
        #     return {"decision": "END"}

        # # refine nếu có
        # refined_step = None
        # if "refine" in judgment.lower():
        #     refined_step = judgment.split("refine:")[-1].strip()
        if state.current_step == 3:
            return {"decision": "END"}

        return {
            "decision": "CONTINUE",
            #"refined_step": refined_step
        }

    # ------------------- CONDITIONAL EDGES ----------------------

    def route_after_verify(self, state: PlannerState):
        if state.decision == "END":
            return "end"
        return "continue"

    # ------------------- CUA TOOL EXECUTION ----------------------

    def node_cua_execute(self, state: PlannerState):
        step = state.refined_step or state.steps[state.current_step]
        obs = step
        print(obs)
        return {
            "step_result": obs,
            "current_step": state.current_step + 1,
            "refined_step": None,
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
                "end": END
            }
        )

        g.add_edge("cua_execute", "verify")

        return g.compile()

    # ------------------- RUN ----------------------

    def run(self, query: str):
        initial = PlannerState(query=query)
        return self.graph.invoke(initial)