"""External integration test against real uvicorn subprocess (not TestClient)."""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
PORT = 8012
BASE = f"http://127.0.0.1:{PORT}"


def _wait_health(timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def uvicorn_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT / "backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert _wait_health(), "external uvicorn failed to start"
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_external_client_against_uvicorn(uvicorn_server, monkeypatch):
    """Drive scripts/backend_launch_client.py against live server."""
    import importlib.util

    monkeypatch.setenv("BASE_OVERRIDE", BASE)  # not used yet
    spec = importlib.util.spec_from_file_location("blc", SCRIPTS / "backend_launch_client.py")
    blc = importlib.util.module_from_spec(spec)
    # Patch module globals for port
    spec.loader.exec_module(blc)
    blc.BASE = BASE
    blc.WS_BASE = f"ws://127.0.0.1:{PORT}"

    import re

    lines: list[str] = []
    blc.run_once("external", lines)
    assert any("ws_first_type=snapshot" in ln for ln in lines)
    post_eq = None
    for ln in lines:
        m = re.search(r"post_equity_p1=([\d.]+)", ln)
        if m:
            post_eq = float(m.group(1))
    assert post_eq is not None and post_eq != 100.0
    replay_eq = None
    for ln in lines:
        if ln.startswith("replay_p1_equity="):
            replay_eq = float(ln.split("=", 1)[1])
    assert replay_eq is not None and replay_eq != 100.0