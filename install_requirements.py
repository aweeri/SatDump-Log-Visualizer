import subprocess
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

def install_requirements():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ All packages installed successfully!")
    except subprocess.CalledProcessError as e:
        print("❌ Failed to install packages.")
        print(e)

if __name__ == "__main__":
    install_requirements()
    input("Press Enter to exit...")
