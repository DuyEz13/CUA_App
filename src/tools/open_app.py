import subprocess
import shutil
import json
import argparse


def open_windows_app(app_name: str):
    """
    Open a Windows application by its name.
    
    Description:
        This utility searches for an application by name
        and attempts to open it. It first checks common executable locations
        (using PATH), and if not found, it uses Windows PowerShell's Start-Process
        with Get-StartApps to find installed apps (like Edge, Spotify, Calculator, etc.).
        
    Parameters:
        app_name (str): The display name or executable name of the application.
        
    Process:
        1. Try to locate .exe using system PATH
        2. If not found, use PowerShell search for registered Start Menu apps
        3. If found, launch app and return success signal
        4. If not found, return failure feedback
        
    Returns:
        dict: A JSON-safe dictionary response for the agent, e.g.:
            {
                "status": "success",
                "message": "Opened Microsoft Edge successfully."
            }
        or
            {
                "status": "failed",
                "message": "Application 'Edge' not found on this system."
            }
    """
    try:
        # Step 1: Try to find the .exe via PATH
        app_path = shutil.which(app_name)
        if app_path:
            subprocess.Popen(app_path)
            return {"status": "success", "message": f"Opened '{app_name}' successfully via PATH."}

        # Step 2: Try PowerShell to search for Start Menu app
        ps_command = (
            f'powershell -Command "'
            f'$app = Get-StartApps | Where-Object {{ $_.Name -like \'*{app_name}*\' }} | Select-Object -First 1; '
            f'if ($app) {{ Start-Process $app.AppId; Write-Output \'FOUND\' }} else {{ Write-Output \'NOTFOUND\' }}"'
        )
        result = subprocess.run(ps_command, shell=True, capture_output=True, text=True)
        print(result.stdout)

        if result.stdout.strip()=='FOUND':
            return {"status": "success", "message": f"Opened '{app_name}' successfully via PowerShell search."}
        else:
            return {"status": "failed", "message": f"Application '{app_name}' not found on this system."}

    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


if __name__ == "__main__":
    # CLI interface for agent or developer
    parser = argparse.ArgumentParser(
        description="Search and open a Windows application by name."
    )
    parser.add_argument(
        "--app", "-a",
        type=str,
        required=True,
        help="The name of the application to open (e.g. 'Edge', 'notepad', 'Spotify')."
    )
    args = parser.parse_args()

    # Run the open_app function with CLI input
    feedback = open_windows_app(args.app)
    print(json.dumps(feedback, indent=4))