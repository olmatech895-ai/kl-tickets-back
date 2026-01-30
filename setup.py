"""Setup script for the backend project"""
import subprocess
import sys
import os


def install_requirements():
    """Install Python requirements"""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Requirements installed successfully!")


def create_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print("Creating .env file from .env.example...")
            with open(".env.example", "r") as example:
                with open(".env", "w") as env:
                    env.write(example.read())
            print(".env file created!")
        else:
            print("Warning: .env.example not found")
    else:
        print(".env file already exists")


if __name__ == "__main__":
    print("Setting up backend project...")
    install_requirements()
    create_env_file()
    print("\nSetup complete!")
    print("\nTo run the server, use:")
    print("  python run.py")
    print("  or")
    print("  uvicorn app.main:app --reload")

