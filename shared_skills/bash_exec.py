import subprocess

def run_bash_command(command: str, cwd: str = ".") -> str:
    """Runs a bash command and returns the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=120
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Error executing command: {e}"
