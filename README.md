# Environment setup
## Create virtual environment
uv venv

## Active env
.venv\Scripts\activate

## Install dependencies
uv sync or pip install -r requirements.txt

## Add API Key
Add Google API Key in app_test.py and CUA_App/src/tools/computer_use/AgentS/cli_app.py.

# How to run
Modify screenshot folder path in CUA_App/src/tools/computer_use/AgentS/cli_app.py.

<pre> ```cd src``` </pre>

python app_test.py. 

While the application is running, if a task encounters a situation requiring user intervention (e.g., login or CAPTCHA), the application will pause and display a notification. The user completes the required action, types ‘continue’ in the application’s chat window, and then minimizes the application window to allow the task to resume. Once the task is completed, the application will notify the user to review the result.

# Demo
https://github.com/user-attachments/assets/28b020a0-d327-4bd7-bb3c-f5f34ac42ae0
