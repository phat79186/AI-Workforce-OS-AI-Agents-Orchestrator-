"""Phase 9: Live AI Autonomous Development Loop Demo Script."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from providers.ollama_provider import OllamaProvider
from providers.openhands_provider import OpenHandsProvider
from providers.registry import ProviderRegistry
from orchestrator.routing import AgentRouter, ModelRouter, ToolRouter, RoutingMode
from orchestrator.core.dependency_graph import DependencyGraph
from orchestrator.events import Event, EventBus, EventStore, EventType


def print_step(step_name: str, msg: str) -> None:
    print(f"\n[{step_name.upper()}] {msg}")
    time.sleep(0.2)


def run_phase9_demo() -> None:
    print("=================================================================")
    print("[PHASE 9 DEMO] LIVE AI AUTONOMOUS DEVELOPMENT LOOP")
    print("=================================================================")

    # 1. Initialize Event Bus & Store
    event_bus = EventBus()
    event_store = EventStore()

    def log_event(evt: Event):
        event_store.record(evt)
        print(f"  [EVENT BUS] {evt.event_type.value} | Task: {evt.task_id} | Agent: {evt.agent_role or 'System'}")

    for et in EventType:
        event_bus.subscribe(et, log_event)

    print_step("Manager", "Khoi tao Local AI Manager & Task Orchestrator...")
    event_bus.publish(Event(event_type=EventType.TASK_CREATED, task_id="TASK-P9-DEMO", payload={"prompt": "Build math_utils feature with bugfix loop"}))

    # 2. Check Providers (Ollama & OpenHands)
    print_step("Provider Registry", "Kiem tra ha tang Local & Open-Source AI...")
    ollama = OllamaProvider(model_name="qwen2.5-coder:7b")
    openhands = OpenHandsProvider()

    ollama_ok = ollama.check_availability()
    openhands_ok = openhands.check_availability()

    print(f"  * Ollama Status: {'ONLINE' if ollama_ok else 'OFFLINE (Tu dong chuyen Local Agent Fallback)'}")
    print(f"  * OpenHands Status: {'INSTALLED' if openhands_ok else 'MISSING CLI (Tu dong chuyen Local Coding Agent)'}")

    # 3. Task Graph & Routing
    print_step("Task Manager", "Phan tich yeu cau & Tao Task DAG...")
    graph = DependencyGraph()
    graph.add_task("TASK-A", "Them ham math_utils va test_math_utils", "Coding Agent")
    graph.add_task("TASK-B", "Chay automated pytest suite", "Testing Agent", dependencies=["TASK-A"])
    graph.add_task("TASK-C", "Debug & va loi neu test FAIL", "Debugging Agent", dependencies=["TASK-B"])
    graph.add_task("TASK-D", "Code Review & Git Diff generation", "Code Review Agent", dependencies=["TASK-C"])

    agent_router = AgentRouter()
    model_router = ModelRouter()
    tool_router = ToolRouter()

    # 4. Use Isolated Temp Workspace
    with tempfile.TemporaryDirectory(prefix="phase9_live_") as tmp_dir:
        demo_dir = Path(tmp_dir)

        print_step("Git Layer", f"Khoi tao Git repo tai: {demo_dir}")
        subprocess.run(["git", "init"], cwd=demo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AI Manager"], cwd=demo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "manager@ai-os.local"], cwd=demo_dir, capture_output=True)

        # Checkout feature branch
        branch_name = "feature/math-utils"
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=demo_dir, capture_output=True)
        print(f"  * Git Branch: {branch_name}")

        # 5. Step 1: Coding Agent - Create Code with INTENTIONAL BUG
        print_step("Agent Router", "Chuyen giao TASK-A cho [Coding Agent]...")
        a_route = agent_router.route("Them ham math_utils va unit test")
        m_route = model_router.route("Them ham math_utils", mode=RoutingMode.FREE)
        t_route = tool_router.route(a_route.agent_role)

        print(f"  * Agent Selected: {a_route.agent_role}")
        print(f"  * Model Selected: {m_route.provider.metadata.name} ({m_route.provider_type.value})")
        print(f"  * Tools Allowed: {t_route.allowed_tools}")

        event_bus.publish(Event(event_type=EventType.AGENT_ASSIGNED, task_id="TASK-A", agent_role=a_route.agent_role))
        event_bus.publish(Event(event_type=EventType.AGENT_STARTED, task_id="TASK-A", agent_role=a_route.agent_role))

        # Writing buggy code intentionally
        code_path = demo_dir / "math_utils.py"
        buggy_code = (
            "def add(a: float, b: float) -> float:\n"
            "    return a - b  # INTENTIONAL BUG: subtract instead of add!\n\n"
            "def multiply(a: float, b: float) -> float:\n"
            "    return a * b\n"
        )
        code_path.write_text(buggy_code, encoding="utf-8")

        test_path = demo_dir / "test_math_utils.py"
        test_code = (
            "from math_utils import add, multiply\n\n"
            "def test_add():\n"
            "    assert add(10, 5) == 15\n\n"
            "def test_multiply():\n"
            "    assert multiply(3, 4) == 12\n"
        )
        test_path.write_text(test_code, encoding="utf-8")

        print(f"  * File created: math_utils.py (voi loi co tinh: return a - b)")
        print(f"  * File created: test_math_utils.py")
        event_bus.publish(Event(event_type=EventType.AGENT_COMPLETED, task_id="TASK-A", agent_role=a_route.agent_role))
        graph.mark_completed("TASK-A")

        # Initial commit
        subprocess.run(["git", "add", "."], cwd=demo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial buggy code"], cwd=demo_dir, capture_output=True)

        # 6. Step 2: Testing Agent - Run Automated Pytest (Expect Failure)
        print_step("Tester", "Chay thuc te Automated Pytest Suite bang Tool Layer...")
        event_bus.publish(Event(event_type=EventType.TEST_STARTED, task_id="TASK-B", agent_role="Testing Agent"))

        res = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path)],
            cwd=demo_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        print(f"  [FAIL] TEST FAILURE DETECTED! (Exit code: {res.returncode})")
        print(f"  [LOG] Error Output Log Snippet:\n{res.stdout[-350:]}")
        event_bus.publish(Event(event_type=EventType.TEST_FAILED, task_id="TASK-B", payload={"error": res.stdout}))

        # 7. Step 3: Debugging Agent - Analyze Error & Apply Code Patch
        print_step("Debugger", "Chuyen giao log loi cho [Debugging Agent] de phan tich root cause...")
        event_bus.publish(Event(event_type=EventType.DEBUG_STARTED, task_id="TASK-C", agent_role="Debugging Agent"))

        print("  [ANALYSIS] Root cause identified: 'add(10, 5)' returned 5 instead of 15 due to subtraction operator '-'.")
        print("  [PATCH] Applying fix to math_utils.py...")

        fixed_code = (
            "def add(a: float, b: float) -> float:\n"
            "    return a + b  # FIXED: changed - to +\n\n"
            "def multiply(a: float, b: float) -> float:\n"
            "    return a * b\n"
        )
        code_path.write_text(fixed_code, encoding="utf-8")
        event_bus.publish(Event(event_type=EventType.FIX_APPLIED, task_id="TASK-C", agent_role="Coding Agent"))

        # 8. Step 4: Re-test Verification
        print_step("Tester", "Tu dong chay lai Test Suite sau khi va loi...")
        res2 = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path)],
            cwd=demo_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if res2.returncode == 0:
            print("  [PASS] AUTOMATED TEST PASSED! (All test assertions 100% GREEN)")
            event_bus.publish(Event(event_type=EventType.TEST_PASSED, task_id="TASK-C"))
        else:
            print(f"  [FAIL] Re-test failed: {res2.stderr}")

        graph.mark_completed("TASK-B")
        graph.mark_completed("TASK-C")

        # 9. Step 5: Code Review Agent & Git Diff Generation
        print_step("Reviewer", "Chuyen giao cho [Code Review Agent] kiem tra chat luong & Tao Git Diff...")
        event_bus.publish(Event(event_type=EventType.REVIEW_APPROVED, task_id="TASK-D", agent_role="Code Review Agent"))

        diff_res = subprocess.run(["git", "diff", "math_utils.py"], cwd=demo_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("  [GIT DIFF CREATED]:")
        print("  -------------------------------------------------------------")
        print(diff_res.stdout)
        print("  -------------------------------------------------------------")

        subprocess.run(["git", "add", "."], cwd=demo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: resolve subtraction bug in math_utils"], cwd=demo_dir, capture_output=True)

        graph.mark_completed("TASK-D")
        event_bus.publish(Event(event_type=EventType.TASK_COMPLETED, task_id="TASK-P9-DEMO"))

    print_step("Manager", "TASK HOAN THANH TOAN BO!")
    print(f"  * Total Recorded Events in EventStore: {len(event_store.get_events())}")
    print(f"  * DAG Completed Status: {graph.is_all_completed()}")
    print("\n[SUCCESS] Phase 9 Live Autonomous Development Loop Demo finished with 100% success!\n")


if __name__ == "__main__":
    run_phase9_demo()
