from agents.graph import PlannerGraph
from agents.planner_state import PlannerState
import time
from langgraph.types import Command

engine_params = {
    "engine_type": "gemini",
    "model": "gemini-2.5-flash",
    "base_url": "https://generativelanguage.googleapis.com/v1beta",
    "api_key": "AIzaSyCWS1fiOUITpUbNtLRGnxK4o92lF0IJF50",
    "temperature": None,
}

config = {
            "configurable": {
                "thread_id": "planner",
            }
        }

if __name__ == "__main__":
    graph = PlannerGraph(engine_params=engine_params)

    query = "Open Edge, go to Google Drive, sign in and find Test case 5 folder"

    result = graph.run(query)

    while "__interrupt__" in result:
        reason = result['__interrupt__'][-1].value
        print(reason)
        user_input = input("User interaction need, please press Enter or type 'continue' to resume: ").strip().lower()
        if user_input in ['', 'continue']:
            time.sleep(3)
            result = graph.graph.invoke(Command(resume=True), config=config)
        else:
            print("Invalid input. Try 'continue' or Enter.")
            result = graph.graph.invoke(Command(resume=False), config=config)
    print(result)