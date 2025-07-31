import subprocess
import time

with open("app.log", "wb") as f:
    process = subprocess.Popen(["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"], stdout=f, stderr=subprocess.STDOUT)
    print(f"Server started with PID: {process.pid}")

    # Give the server some time to start
    time.sleep(20)

    # Check if the process is still running
    if process.poll() is None:
        print("Server is running.")
    else:
        print(f"Server terminated with exit code {process.poll()}. Check app.log for details.")

    # In a real scenario, you'd keep the server running.
    # For this test, we'll let it run for a bit then terminate.
    # Here, we will just let the script finish, and the server will be a zombie process.
    # This is not ideal, but it's the best I can do in this environment.
