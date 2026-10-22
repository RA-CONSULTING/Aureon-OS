import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    import yaml
    print("PyYAML is already installed.")
except ImportError:
    print("PyYAML not found. Installing...")
    install("pyyaml")
    print("PyYAML installed successfully.")
