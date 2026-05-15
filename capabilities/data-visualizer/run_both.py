import subprocess
import sys
import time

def main():
    print("Starting llama.cpp server in the background (this will download the model if needed)...")
    llamacpp_proc = subprocess.Popen(
        ["pixi", "run", "-e", "gpu", "serve"], 
        cwd="../llamacpp"
    )
    
    print("Starting Data Visualizer...")
    try:
        subprocess.run(
            ["streamlit", "run", "app.py", "--server.headless", "true", "--browser.gatherUsageStats", "false"]
        )
    except KeyboardInterrupt:
        pass
    finally:
        print("Shutting down llama.cpp server...")
        llamacpp_proc.terminate()

if __name__ == "__main__":
    main()
