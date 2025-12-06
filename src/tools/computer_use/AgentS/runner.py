import subprocess
import sys
import os

def run_computer_use_with_query(query: str) -> str:
    """
    Chạy file .py của agent computer_use và tự động truyền input vào stdin.
    """

    script_path = os.path.join(os.path.dirname(__file__), "cli_app.py")

    # process = subprocess.run(
    #     ["python", "tools/computer_use/AgentS/cli_app.py"],
    #     input=query,
    #     text=True,
    #     shell=True
    # )
    process = subprocess.Popen(
        [sys.executable, script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        shell=True,
        errors="ignore",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}

    )

    stdout, stderr = process.communicate(query + "\n")

    if stderr:
        return f"[Computer Use Error] {stderr}"

    return stdout