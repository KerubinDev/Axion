import subprocess
import sys
import os
from pathlib import Path

def build():
    print("🚀 Starting AkitaLLM Binary Build Process...")
    
    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Define parameters
    entry_point = "akita/cli/main.py"
    output_name = "akita"
    
    # Tree-sitter needs to include its shared libraries/languages
    # We include them as data files if needed, but for now we try a simple build
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--console",
        "--name", output_name,
        # Tree-sitter hidden imports
        "--hidden-import", "tree_sitter_python",
        # Entry point
        entry_point
    ]

    print(f"📦 Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n✅ Build SUCCESSFUL! Binary located in 'dist/{output_name}.exe'")
    else:
        print(f"\n❌ Build FAILED with code {result.returncode}")

if __name__ == "__main__":
    build()
