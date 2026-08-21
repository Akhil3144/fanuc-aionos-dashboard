#!/usr/bin/env python3
"""Verify factual routing and explanation fallback with the AI layer off/on."""
import json
import subprocess
import time
from pathlib import Path

import ask_routes

ROOT = Path(__file__).resolve().parent.parent
registry = json.loads(subprocess.check_output(
    ["node", "-e", "import('./src/data/robotRegistry.js').then(m=>console.log(JSON.stringify(m.robotRegistry)))"],
    cwd=ROOT, text=True,
))

FAST = [
    ("How many robots are in the Open House registry?", None), ("Which robot is used for AI Error Proofing?", None),
    ("Which robot is used for RTU Cell?", None), ("Which robots are featured?", None),
    ("What model is OH26-R013?", "OH26-R013"), ("What application is OH26-R019 used for?", "OH26-R019"),
    ("What is the IP address of OH26-R013?", "OH26-R013"), ("What is the current OEE?", "OH26-R013"),
    ("What is the current cycle time?", "OH26-R013"), ("What is the current state?", "OH26-R013"),
    ("What is the current power consumption?", "OH26-R019"), ("Which axis has the highest load?", "OH26-R019"),
    ("Are there active alarms?", "OH26-R013"), ("Is maintenance due?", "OH26-R013"),
    ("Which robot has the lowest OEE?", None), ("Which robot has the highest OEE?", None),
    ("Which robot has the highest current power consumption?", None), ("Which robots have active alarms?", None),
    ("Which robot has overdue maintenance?", None), ("How many robots are currently running?", None),
]
AI = [
    ("Give me an executive summary of this robot.", "OH26-R013"),
    ("Explain why this robot needs attention.", "OH26-R019"),
    ("Summarize the important changes in recent telemetry.", "OH26-R013"),
    ("What should an engineer inspect first and why?", "OH26-R019"),
    ("Give me an overall fleet risk summary.", None),
]

def ask(question, robot_id):
    return ask_routes.ask_my_robot(ask_routes.AskRobotRequest(
        question=question, selected_robot_id=robot_id or "OH26-R001",
        selected_registry_id=robot_id, robot_registry=registry,
    ))

def run_mode(ai_available):
    original = ask_routes.ask_ollama
    ask_routes.ask_ollama = (lambda question, evidence: "Grounded AI explanation from compact calculated evidence.") if ai_available else (lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unavailable")))
    try:
        started = time.perf_counter()
        fast = [ask(q, r) for q, r in FAST]
        elapsed = (time.perf_counter() - started) / len(fast)
        explanations = [ask(q, r) for q, r in AI]
        expected = "AI" if ai_available else "AI_FALLBACK"
        return sum(item.get("resolution_mode") == "DETERMINISTIC" for item in fast), sum(bool(item.get("resolution_mode") == expected and item.get("answer")) for item in explanations), elapsed
    finally:
        ask_routes.ask_ollama = original

off_fast, off_ai, avg = run_mode(False)
on_fast, on_ai, _ = run_mode(True)
print("OLLAMA OFF")
print(f"Deterministic: {off_fast}/20")
print(f"AI fallback: {off_ai}/5")
print("OLLAMA ON")
print(f"Deterministic: {on_fast}/20")
print(f"AI questions: {on_ai}/5")
print(f"Deterministic average seconds: {avg:.4f}")
raise SystemExit(0 if (off_fast, off_ai, on_fast, on_ai) == (20, 5, 20, 5) else 1)
