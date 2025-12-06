from langchain.tools import tool
from tools.computer_use.AgentS.runner import run_computer_use_with_query

@tool
def computer_use(query: str) -> str:
    """
    Tool gọi agent computer_use bằng cách chạy file python + gửi input.
    """
    result = run_computer_use_with_query(query)
    return result