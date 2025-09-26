#!/usr/bin/env python3
"""
Backend server runner script for hosting
"""
import subprocess
import sys
import os
import platform


def get_venv_python() -> str:
    """Return the backend venv python if it exists, else current interpreter."""
    if platform.system() == 'Windows':
        candidate = os.path.join('.venv', 'Scripts', 'python.exe')
    else:
        candidate = os.path.join('.venv', 'bin', 'python')
    return candidate if os.path.exists(candidate) else sys.executable


def main():
    """Run the FastAPI backend server"""
    # We're already in the backend directory for hosting
    python_exec = get_venv_python()

    # Run the server
    try:
        subprocess.run([python_exec, 'main.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running backend server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBackend server stopped.")
        sys.exit(0)


if __name__ == '__main__':
    main()
