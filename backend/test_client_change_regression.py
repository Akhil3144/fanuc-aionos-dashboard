#!/usr/bin/env python3
"""Focused regressions for the controlled client enhancement pass."""
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "http://127.0.0.1:8000/ask-my-robot"
registry = json.loads(subprocess.check_output(
    ["node", "-e", "import('./src/data/robotRegistry.js').then(m=>console.log(JSON.stringify(m.robotRegistry)))"], cwd=ROOT, text=True
))
snapshots = {item["robot_id"]: item for item in json.loads((ROOT / "public/data_openhouse/robot_current.json").read_text())}

def ask(question, scope="FLEET", robot_id=None):
    payload = {"question": question, "scope": scope, "robot_id": robot_id, "selected_robot_id": robot_id,
               "selected_registry_id": robot_id, "live_snapshot": snapshots.get(robot_id), "robot_registry": registry}
    request = urllib.request.Request(API, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())

checks = [
    ("What robot am I viewing?", "ROBOT", "OH26-R013", "OH26-R013"),
    ("What model is this?", "ROBOT", "OH26-R013", "LR-Mate 7-9D"),
    ("What application is this robot used for?", "ROBOT", "OH26-R019", "RTU Cell"),
    ("Find all collaborative robots.", "FLEET", None, "13 CRX collaborative robots"),
    ("Which robots are CRX robots?", "FLEET", None, "OH26-R029"),
    ("Compare OH26-R013 and OH26-R019.", "FLEET", None, "OH26-R013"),
    ("Which robots need attention?", "FLEET", None, "attention"),
    ("Which three robots should be inspected first?", "FLEET", None, "OH26-R028"),
]
for question, scope, robot_id, expected in checks:
    result = ask(question, scope, robot_id)
    answer = result.get("answer", "")
    assert expected.lower() in answer.lower(), (question, answer)
    print(f"PASS {question} | {result.get('query_scope')}")
