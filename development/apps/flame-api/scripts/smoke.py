"""Run a short real HTTP smoke check and stop only the server we start."""
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
     "--port", str(port), "--no-access-log"], cwd=root,
)
try:
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError("Server exited before startup")
        try:
            with urlopen(f"http://127.0.0.1:{port}/health/live", timeout=1) as response:
                assert response.status == 200
                print("HTTP liveness:", response.status, response.read().decode())
                break
        except URLError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Server did not start")
    try:
        with urlopen(f"http://127.0.0.1:{port}/health/ready", timeout=10) as response:
            print("HTTP readiness:", response.status)
    except HTTPError as error:
        assert error.code == 503
        print("HTTP readiness:", error.code, "(database not configured/available)")
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
