import time
from langgraph.errors import GraphInterrupt

# def tool_pause_for_user(reason: str):
#     """
#     Print fail reasons from cua agent and stop the graph for users to interact with screen
    
#     :param reason: Description
#     :type reason: str
#     """
#     # Lý do tạm dừng để hiển thị cho user
#     print(f"PAUSE: {reason}")
    
#     # Dừng graph
#     # raise GraphInterrupt(
#     #     "user_intervention_required",
#     #     payload={"reason": reason}
#     # )

def tool_pause_for_user(reason: str):
    """
    Print fail reasons from cua agent and stop the graph for users to interact with screen
    
    :param reason: Description
    :type reason: str
    """
    return {
        "interrupt": {
            "type": "USER_REQUIRED",
            "reason": reason
        }
    }

def tool_debug_print(text: str):
    """
    Print fail reasons from cua agent.
    """
    print("[DEBUG TOOL]", text)
    return "printed"
