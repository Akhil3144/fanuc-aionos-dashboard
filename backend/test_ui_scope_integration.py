#!/usr/bin/env python3
"""POST browser-shaped Ask My Robot payloads and verify page scope."""
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "http://127.0.0.1:8000/ask-my-robot"
registry = json.loads(subprocess.check_output(
    ["node", "-e", "import('./src/data/robotRegistry.js').then(m=>console.log(JSON.stringify(m.robotRegistry)))"],
    cwd=ROOT, text=True,
))
current = json.loads((ROOT / "public/data_openhouse/robot_current.json").read_text())
snapshots = {item["robot_id"]: item for item in current}

def post(question, scope, robot_id=None):
    payload = {
        "question": question, "live_snapshot": snapshots.get(robot_id),
        "robot_id": robot_id, "selected_robot_id": robot_id, "selected_registry_id": robot_id,
        "scope": scope, "robot_registry": registry,
    }
    request = urllib.request.Request(API, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())

robot_questions = [
    "Which axis has the highest load?", "What is the current OEE?", "Are there active alarms?",
    "Is maintenance due?", "How is current cycle performance?", "What is the current power?",
    "Give me a condition summary.",
]
results = [post(question, "ROBOT", "OH26-R001") for question in robot_questions]
fleet = post("Which robot has the highest axis load?", "FLEET")
axes = snapshots["OH26-R001"]["axis_servo"]
print("OH26-R001 AXES:")
for axis in axes:
    print(f"J{axis['axis']} {axis['axis_load_pct']}%")
for question, result in zip(robot_questions, results):
    print(f"PASS {question} | {result.get('query_scope')} | {result.get('resolution_mode')} | {result.get('answer')}")

robot_ok = all(result.get("query_scope") != "FLEET_COMPARISON" for result in results)
fleet_ok = fleet.get("query_scope") == "FLEET_COMPARISON"
axis_ok = len(axes) == 6 and results[0].get("resolution_mode") == "DETERMINISTIC"
raise SystemExit(0 if robot_ok and fleet_ok and axis_ok else 1)
