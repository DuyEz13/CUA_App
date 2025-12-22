from langgraph.graph import StateGraph, END
from agents.planner_state import PlannerState
from agents.planner import Planner
import fitz
from PIL import Image
from pathlib import Path
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
import time
from agents.token_tracker import TokenUsageLogger

BASE_PATH = r'E:\test2\CUA_App\src\token_log'
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

def pixmap_to_pil(pix: fitz.Pixmap) -> Image.Image:
    mode = "RGB" if pix.n < 4 else "RGBA"
    return Image.frombytes(mode, [pix.width, pix.height], pix.samples)

def pdf_extraction(file, index, output_path, dpi: int=200):
    pdf_path = Path(r"C:\Users\NITRO 5", file)
    doc = fitz.open(pdf_path)
    print(pdf_path)
    page = doc.load_page(int(index) - 1)

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(r"E:\test2\CUA_App\src\pdf_pages\test.png")

    screenshot = pixmap_to_pil(pix)

    buffered = io.BytesIO()
    screenshot.save(buffered, format="PNG")

    screenshot_bytes = buffered.getvalue()

    doc.close()
    return screenshot_bytes

def normalize_to_single_line(text: str) -> str:
    return " ".join(text.split())

class PlannerGraph:
    def __init__(self, engine_params: Dict):
        self.llm = Planner(engine_params)
        self.checkpointer = InMemorySaver()
        self.graph = self.build_graph()
        self.engine_params = engine_params
        self.interrupt_tracker = 0
        self.frl = []

    # NODES

    def node_make_plan(self, state: PlannerState):
        start_time = time.time()
        plan_text, full_rp = self.llm.plan_predict(state.query)
        end_time = time.time()
        print("-" * 60)
        print("Plan making time: ", end_time - start_time)
        print("-" * 60)
        _track_graph_node_tokens(state.current_step, full_rp, self.engine_params['model'], "Planning Agent")
        return {
            "steps": plan_text,
            "current_step": 0,
            "cua_result": None,
            "fail_reason_list": [],
        }
    
    def node_step_verify(self, state: PlannerState):
        if state.current_step == len(state.steps):
            return {
                "decision": "NO_PDF"
            }
        print("-" * 60)
        print("Step verifying.....")
        print("-" * 60)
        response, full_rp = self.llm.step_verify_predict(state.steps[state.current_step])
        _track_graph_node_tokens(state.current_step, full_rp, self.engine_params['model'], "Step Verifying Agent")
        if response[0] == 'F':
            return {
                "form": True,
                "decision": "NO_PDF"
            }
        if response[0] == 'P':
            _, file, index = response.split(' - ')
            print(index)
            img_pdf_page = pdf_extraction(file, index, r"E:\test2\CUA_App\src\pdf_pages")
            return {
                "decision": "PDF",
                "img_pdf_page": img_pdf_page
            }
        else:
            return {
                "decision": "NO_PDF"
            }
    
    def node_A_execute(self, state: PlannerState):
        print(state.form_info)
        result, full_rp = self.llm.pdf_extract(state.steps[state.current_step] + state.form_info, state.img_pdf_page)
        _track_graph_node_tokens(state.current_step, full_rp, self.engine_params['model'], "PDF Extracting Agent")
        result = normalize_to_single_line(result)
        print(result)
        refined_step = state.steps
        refined_step[state.current_step] = result
        return {
            "pdf_info": result,
            "steps": refined_step,
            "img_pdf_page": None,
            "form": False
        }
    
    def route_after_step_verify(self, state: PlannerState):
        if state.decision == "PDF":
            return "PDF_execute"
        return "verify"
    
    def node_interrupt(self, state: PlannerState):
        reason = state.interrupt_reason

        human_approved = interrupt(reason)

        return {
            "human_approved": human_approved,
            "decision": "INTERRUPT_DONE"
        }
    
    def node_verify(self, state: PlannerState):
        if state.current_step == len(state.steps):
            return {"decision": "END"}
        
        if state.human_approved is True:
            return {
                "human_approved": None,
                #"current_step": state.current_step - 1,
                "decision": "RETRY"
            }

        if state.cua_result is not None and state.cua_result["signal"] == "Fail":
            cua_result_str = json.dumps(state.cua_result, ensure_ascii=False)
            start_time = time.time()
            verify_result, full_rp = self.llm.verify_predict(cua_result_str)
            end_time = time.time()
            print("-" * 60)
            print('Verification time: ', end_time - start_time)
            print("-" * 60)
            _track_graph_node_tokens(state.current_step, full_rp, self.engine_params['model'], "Verifying Agent")
            reason = verify_result[2:]

            if verify_result[0] == "A":
                return {
                    "decision": "INTERRUPT",
                    "interrupt_reason": reason,
                    "current_step": state.current_step - 1,
                    "fail_reason_list": state.fail_reason_list + [reason]
                }
            else:
                return {
                    "decision": "RETRY",
                    "current_step": state.current_step - 1,
                    "fail_reason_list": state.fail_reason_list + [reason]
                }

        return {"decision": "CONTINUE"}

    def route_after_verify(self, state):
        if state.decision == "END":
            return "end"
        if state.decision == "INTERRUPT":
            return "interrupt"
        if state.decision == "RETRY":
            return "retry"
        return "continue"

    # CUA EXECUTION

    def node_cua_execute(self, state: PlannerState):
        step = state.refined_step or state.steps[state.current_step]
        print("-" * 60)
        print(step)
        print("-" * 60)
        step = "Only do the following instruction. Do not do anything beside it. " + step
        start_time = time.time()
        response = run_computer_use_with_query(step)
        end_time = time.time()
        print("-" * 60)
        print('Elapsed time:', end_time - start_time)
        print("-" * 60)
        filename = f"cua_step_{state.current_step + 1}.txt"
        file_path = os.path.join(task_path, filename)
        print(file_path)
        cua_result = parse_last_step(response)
        if len(state.fail_reason_list) != 0:
            cua_result['fail_reason_list'] = state.fail_reason_list
        token_log = parse_token_usage(response)
        write_token_log_txt(token_log, file_path)
        print(response)
        if state.form == True:
            return {
                "step_result": step,
                "current_step": state.current_step + 1,
                "response": response,
                "cua_result": cua_result,
                "form_info": cua_result['next_action']
            }
        return {
            "step_result": step,
            "current_step": state.current_step + 1,
            "response": response,
            "cua_result": cua_result,
        }

    def build_graph(self):
        g = StateGraph(PlannerState)

        g.add_node("make_plan", self.node_make_plan)
        g.add_node("step_verify", self.node_step_verify)
        g.add_node("PDF_execute", self.node_A_execute)
        g.add_node("verify", self.node_verify)
        g.add_node("interrupt", self.node_interrupt)
        g.add_node("cua_execute", self.node_cua_execute)

        g.set_entry_point("make_plan")

        g.add_edge("make_plan", "step_verify")

        # g.add_edge("make_plan", "verify")

        g.add_conditional_edges(
            "step_verify",
            self.route_after_step_verify,
            {
                "PDF_execute": "PDF_execute",
                "verify": "verify"
            }
        )

        g.add_conditional_edges(
            "verify",
            self.route_after_verify,
            {
                "continue": "cua_execute",
                "retry": "cua_execute", 
                "interrupt": "interrupt",
                "end": END
            }
        )
        
        g.add_edge("PDF_execute", "verify")

        g.add_edge("interrupt", "verify")

        #g.add_edge("cua_execute", "verify")
        g.add_edge("cua_execute", "step_verify")

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
