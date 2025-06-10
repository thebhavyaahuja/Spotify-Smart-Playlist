import subprocess
import shlex # Import shlex for robust command string parsing

import os
import re

def load_env_var_from_profile():
    bashrc_path = os.path.expanduser("~/.bashrc")  # or use .zshrc / .profile
    try:
        with open(bashrc_path, 'r') as f:
            content = f.read()
        match = re.search(r"export SPOTIFY_ACCESS_TOKEN='([^']+)'", content)
        if match:
            os.environ['SPOTIFY_ACCESS_TOKEN'] = match.group(1)
            print("✅ Loaded SPOTIFY_ACCESS_TOKEN from .bashrc")
        else:
            print("⚠️ SPOTIFY_ACCESS_TOKEN not found in .bashrc")
    except Exception as e:
        print(f"⚠️ Error reading {bashrc_path}: {e}")


def run_script(script_command_string):
    """Runs a python script, allowing for interactive input/output."""
    try:
        print(f"Running {script_command_string}...")
        
        # Use shlex.split to correctly parse the script name and its arguments
        command_parts = shlex.split(script_command_string)
        script_actual_name = command_parts[0]
        script_args = command_parts[1:]
        
        command = ["python3", script_actual_name] + script_args
        
        # Run the script, allowing it to inherit stdin, stdout, and stderr
        # This enables interactive input.
        process = subprocess.Popen(command)
        
        # Wait for the script to complete
        process.communicate() 
        
        if process.returncode == 0:
            print(f"Successfully completed {script_command_string}")
        else:
            print(f"Error running {script_command_string}. Return code: {process.returncode}")
            
    except FileNotFoundError:
        print(f"Error: The file {script_actual_name if 'script_actual_name' in locals() else script_command_string.split()[0]} was not found. Make sure it is in the same directory as app.py or provide the correct path.")
    except Exception as e:
        print(f"An error occurred while running {script_command_string}: {e}")

if __name__ == "__main__":
    load_env_var_from_profile()
    scripts_to_run = [
        "get_token.py",
        "fetch_playlists.py",
        "analyze_playlists.py",
        "autolist_increment.py --init date"
    ]

    for script in scripts_to_run:
        run_script(script)

