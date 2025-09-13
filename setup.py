#!/usr/bin/env python3
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, cwd=None, shell=False):
    """Run a command and handle errors gracefully."""
    try:
        print(f"Running: {' '.join(command) if isinstance(command, list) else command}")
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=shell,
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def get_python_executable():
    """Get the appropriate Python executable for the current platform."""
    python_names = ['python3', 'python', 'py']
    
    for name in python_names:
        try:
            result = subprocess.run([name, '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return name
        except FileNotFoundError:
            continue
    
    # Fallback to sys.executable
    return sys.executable


def get_venv_activation_command():
    """Get the virtual environment activation command for the current OS."""
    system = platform.system().lower()
    
    if system == 'windows':
        return ['.venv\\Scripts\\activate.bat']
    else: 
        return ['source', '.venv/bin/activate']


def get_pip_executable():
    """Get the pip executable path within the virtual environment."""
    system = platform.system().lower()
    
    if system == 'windows':
        return '.venv\\Scripts\\pip.exe'
    else:
        return '.venv/bin/pip'


def main():
    """Main setup function."""
    print("Setting up Twilio ConversationRelay project...")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    # Get project root directory
    project_root = Path(__file__).parent.absolute()
    print(f"Project root: {project_root}")
    
    requirements_file = project_root / 'requirements.txt'
    if not requirements_file.exists():
        print("ERROR: requirements.txt not found!")
        return False
    
    python_exe = get_python_executable()
    print(f"Using Python: {python_exe}")
    
    try:
        result = subprocess.run([python_exe, '--version'], capture_output=True, text=True)
        print(f"Python version: {result.stdout.strip()}")
    except Exception as e:
        print(f"Warning: Could not check Python version: {e}")
    
    # Create virtual environment
    venv_path = project_root / '.venv'
    if venv_path.exists():
        print("Virtual environment already exists at .venv")
        user_input = input("Do you want to recreate it? (y/N): ").strip().lower()
        if user_input in ['y', 'yes']:
            print("Removing existing virtual environment...")
            import shutil
            shutil.rmtree(venv_path)
        else:
            print("Using existing virtual environment")
    
    if not venv_path.exists():
        print("Creating virtual environment...")
        if not run_command([python_exe, '-m', 'venv', '.venv'], cwd=project_root):
            print("ERROR: Failed to create virtual environment!")
            return False
        print("Virtual environment created successfully")
    
    # Install/upgrade pip
    print("Upgrading pip...")
    pip_exe = get_pip_executable()
    pip_path = project_root / pip_exe
    
    if not run_command([str(pip_path), 'install', '--upgrade', 'pip'], cwd=project_root):
        print("WARNING: Could not upgrade pip")
    
    # Install requirements
    print("Installing requirements from requirements.txt...")
    if not run_command([str(pip_path), 'install', '-r', 'requirements.txt'], cwd=project_root):
        print("ERROR: Failed to install requirements!")
        return False
    
    print("Requirements installed successfully")
    
    print("\nSetup completed successfully!")
    print("\nTo activate the virtual environment:")
    
    system = platform.system().lower()
    if system == 'windows':
        print("   Windows (Command Prompt): .venv\\Scripts\\activate.bat")
        print("   Windows (PowerShell):     .venv\\Scripts\\Activate.ps1")
    else:
        print("   Unix/Linux/macOS:        source .venv/bin/activate")
    
    print("\nTo run the application:")
    print("   python app.py")
    
    print("\nTo deactivate the virtual environment:")
    print("   deactivate")
    
    return True


if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)
    
    print("\nSetup complete. You may now begin development.")
