#!/usr/bin/env python3
"""Check every visible prompt with browser-equivalent fields and AI unavailable."""
import json, subprocess
from pathlib import Path
import ask_routes

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = json.loads(subprocess.check_output(["node", "-e", "import('./src/data/robotRegistry.js').then(m=>console.log(JSON.stringify(m.robotRegistry)))"], cwd=ROOT, text=True))
CURRENT = {item["robot_id"]: item for item in json.loads((ROOT / "public/data_openhouse/robot_current.json").read_text())}
FLEET = ["Which robots need the most attention?", "Which robots have overdue maintenance?", "Which robot has the lowest OEE?", "Which robot has the highest axis load?", "Which robots have active alarms?", "How many robots are running?", "Give me an overall fleet risk summary."]
NORMAL = ["What is the current OEE?", "Which axis has the highest load?", "Are there active alarms?", "Is maintenance due?", "How is current cycle time?", "Give me a condition summary."]
FEATURED = ["How far is cycle time from target?", "Which axis has the highest load?", "What maintenance is due?", "How does current power compare with history?", "Is OEE above or below its historical average?", "Give me a complete condition summary.", "What changed recently?", "What should be inspected first?", "Explain the latest alarm in context."]

def run(questions, scope, robot_id=None):
    passed = 0
    for question in questions:
        result = ask_routes.ask_my_robot(ask_routes.AskRobotRequest(question=question, live_snapshot=CURRENT.get(robot_id), robot_id=robot_id, selected_robot_id=robot_id, selected_registry_id=robot_id, scope=scope, robot_registry=REGISTRY))
        result_scope = result.get("query_scope") or ""
        scoped = (result_scope == "FLEET_COMPARISON" or result_scope.startswith("AI_FLEET_")) if scope == "FLEET" else result_scope != "FLEET_COMPARISON" and not result_scope.startswith("AI_FLEET_")
        forbidden = any(value in str(result.get("answer")) for value in ("EXH-R01", "EXH-R02", "EXH-R03", "R01-MNT", "R02-MNT", "R03-MNT"))
        resolved = True if scope == "FLEET" else result.get("resolved_robot_id") == robot_id and result.get("data_source") == "OPENHOUSE"
        passed += bool(result.get("answer") and scoped and resolved and not forbidden)
    return passed

original = ask_routes.ask_ollama
ask_routes.ask_ollama = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unavailable"))
try:
    scores = {"Fleet": (run(FLEET, "FLEET"), len(FLEET)), "OH26-R006": (run(NORMAL, "ROBOT", "OH26-R006"), len(NORMAL)), "R017": (run(NORMAL, "ROBOT", "OH26-R017"), len(NORMAL)), "R013": (run(FEATURED, "ROBOT", "OH26-R013"), len(FEATURED)), "R019": (run(FEATURED, "ROBOT", "OH26-R019"), len(FEATURED))}
finally:
    ask_routes.ask_ollama = original
for name, score in scores.items(): print(f"{name}: {score[0]}/{score[1]}")
raise SystemExit(0 if all(a == b for a, b in scores.values()) else 1)
