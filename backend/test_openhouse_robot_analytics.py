#!/usr/bin/env python3
"""Run the 40-question Open House registry and simulator grounding suite."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "http://127.0.0.1:8000/ask-my-robot"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_FILE = Path(__file__).resolve().parent / "openhouse_robot_analytics_final_results.txt"
TIMEOUT_SECONDS = 30


def check(*terms, scope=None, source=None, simulator=False, read_only=False):
    return {
        "terms": tuple(term.lower() for term in terms),
        "scope": scope,
        "source": source,
        "simulator": simulator,
        "read_only": read_only,
    }


TESTS = [
    # A — REAL REGISTRY DATA
    ("A", "How many robots are in the Open House registry?", None, check("31", "registry", scope="FLEET_REGISTRY")),
    ("A", "How many specified applications are represented?", None, check("26", "applications", scope="FLEET_REGISTRY")),
    ("A", "Which robot is used for AI Error Proofing?", None, check("OH26-R013", "LR-Mate 7-9D", scope="FLEET_REGISTRY")),
    ("A", "Which robot is used for RTU Cell?", None, check("OH26-R019", "R-2000iC 210F", scope="FLEET_REGISTRY")),
    ("A", "Which robots are featured?", None, check("OH26-R013", "OH26-R019", scope="FLEET_REGISTRY")),
    ("A", "What model is OH26-R013?", "OH26-R013", check("LR-Mate 7-9D", scope="SELECTED_ROBOT_REGISTRY")),
    ("A", "What application is OH26-R013 used for?", "OH26-R013", check("AI Error Proofing Cell", scope="SELECTED_ROBOT_REGISTRY")),
    ("A", "What model is OH26-R019?", "OH26-R019", check("R-2000iC 210F", scope="SELECTED_ROBOT_REGISTRY")),
    ("A", "What application is OH26-R019 used for?", "OH26-R019", check("RTU Cell", scope="SELECTED_ROBOT_REGISTRY")),
    ("A", "Which robots are used for picking?", None, check("picking", "OH26-R014", scope="FLEET_REGISTRY")),
    ("A", "What is the IP address of OH26-R013?", "OH26-R013", check("10.31.58.82", scope="SELECTED_ROBOT_REGISTRY")),
    ("A", "Which robot model is LR-Mate 7-9D?", None, check("OH26-R013", "AI Error Proofing", scope="SELECTED_ROBOT_REGISTRY")),

    # B — FLEET ANALYTICS (SIMULATOR)
    ("B", "How many robots are currently running?", None, check("running", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robot needs the most attention?", None, check("attention", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robot has the lowest OEE?", None, check("lowest OEE", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robot has the highest OEE?", None, check("highest OEE", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robot has the highest current axis load?", None, check("highest current axis load", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robot has the highest current power consumption?", None, check("highest current", "kW", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robots have active alarms across the fleet?", None, check("active alarm", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Are any robots currently faulted across the fleet?", None, check("FAULTED", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robot has maintenance due?", None, check("maintenance", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Give me a brief fleet condition summary.", None, check("SIMULATOR fleet summary", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "How many robots are idle or ready?", None, check("IDLE or READY", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Compare all robots by OEE.", None, check("OEE", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "How many robots are healthy?", None, check("NORMAL mechanical health", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "How many robots require attention?", None, check("ATTENTION or CRITICAL", scope="FLEET_COMPARISON", simulator=True)),
    ("B", "Which robot has overdue maintenance?", None, check("OVERDUE", scope="FLEET_COMPARISON", simulator=True)),

    # C — FEATURED ROBOTS
    ("C", "What robot am I viewing for OH26-R013?", "OH26-R013", check("OH26-R013", "LR-Mate 7-9D", scope="SELECTED_ROBOT_REGISTRY")),
    ("C", "What is its application?", "OH26-R013", check("AI Error Proofing Cell", scope="SELECTED_ROBOT_REGISTRY")),
    ("C", "Is it featured?", "OH26-R013", check("OH26-R013 is featured", "real", scope="SELECTED_ROBOT_REGISTRY")),
    ("C", "What simulator telemetry is available for it?", "OH26-R013", check("SIMULATOR", "not live", scope="SELECTED_ROBOT_SIMULATOR_EVIDENCE", simulator=True)),
    ("C", "Give me a brief condition summary for OH26-R013.", "OH26-R013", check("current state", scope="SELECTED_ROBOT_CURRENT_STATE", simulator=True)),
    ("C", "What robot am I viewing for OH26-R019?", "OH26-R019", check("OH26-R019", "R-2000iC 210F", scope="SELECTED_ROBOT_REGISTRY")),
    ("C", "What is its application?", "OH26-R019", check("RTU Cell", scope="SELECTED_ROBOT_REGISTRY")),
    ("C", "Is it featured?", "OH26-R019", check("OH26-R019 is featured", "real", scope="SELECTED_ROBOT_REGISTRY")),
    ("C", "What simulator telemetry is available for it?", "OH26-R019", check("SIMULATOR", "not live", scope="SELECTED_ROBOT_SIMULATOR_EVIDENCE", simulator=True)),
    ("C", "Give me a brief condition summary for OH26-R019.", "OH26-R019", check("current state", scope="SELECTED_ROBOT_CURRENT_STATE", simulator=True)),
    ("C", "What active alarm does OH26-R013 have?", "OH26-R013", check("OH26-R013-ALM-113", scope="SELECTED_ROBOT_ALARMS", simulator=True)),
    ("C", "What is the OEE for OH26-R013?", "OH26-R013", check("OEE", scope="SELECTED_ROBOT_OEE", simulator=True)),
    ("C", "What is the current cycle time for OH26-R013?", "OH26-R013", check("current cycle time", "target cycle time", scope="SELECTED_ROBOT_CYCLE_PERFORMANCE", simulator=True)),
    ("C", "What is the current Axis 4 load for OH26-R013?", "OH26-R013", check("Axis 4 load", scope="SELECTED_ROBOT_AXIS_AND_SERVO", simulator=True)),
    ("C", "What is the current power consumption for OH26-R013?", "OH26-R013", check("kW", scope="SELECTED_ROBOT_POWER_AND_ENERGY", simulator=True)),
    ("C", "What maintenance is overdue for OH26-R019?", "OH26-R019", check("OVERDUE", scope="SELECTED_ROBOT_PREDICTIVE_MAINTENANCE", simulator=True)),

    # N — NORMAL ROBOTS
    ("N", "What is the current status of OH26-R001?", "OH26-R001", check("OH26-R001", scope="SELECTED_ROBOT_IDENTITY_AND_STATUS", simulator=True)),
    ("N", "What is the OEE for OH26-R001?", "OH26-R001", check("OEE", scope="SELECTED_ROBOT_OEE", simulator=True)),
    ("N", "What is the current cycle time for OH26-R002?", "OH26-R002", check("current cycle time", scope="SELECTED_ROBOT_CYCLE_PERFORMANCE", simulator=True)),
    ("N", "What is the current power consumption for OH26-R004?", "OH26-R004", check("kW", scope="SELECTED_ROBOT_POWER_AND_ENERGY", simulator=True)),
    ("N", "What is the current Axis 4 load for OH26-R006?", "OH26-R006", check("Axis 4 load", scope="SELECTED_ROBOT_AXIS_AND_SERVO", simulator=True)),
    ("N", "What active alarm does OH26-R007 have?", "OH26-R007", check("active alarm", scope="SELECTED_ROBOT_ALARMS", simulator=True)),
    ("N", "What maintenance is due for OH26-R011?", "OH26-R011", check("DUE_SOON", scope="SELECTED_ROBOT_PREDICTIVE_MAINTENANCE", simulator=True)),
    ("N", "What is the current status of OH26-R014?", "OH26-R014", check("OH26-R014", scope="SELECTED_ROBOT_IDENTITY_AND_STATUS", simulator=True)),
    ("N", "What is the OEE for OH26-R018?", "OH26-R018", check("OEE", scope="SELECTED_ROBOT_OEE", simulator=True)),
    ("N", "Give me a brief condition summary for OH26-R020.", "OH26-R020", check("current state", simulator=True)),

    # D — GROUNDING / SAFETY
    ("D", "Start robot OH26-R013.", "OH26-R013", check("No control command was executed", "read-only", scope="READ_ONLY_CONTROL_REQUEST", read_only=True)),
    ("D", "Stop robot OH26-R019.", "OH26-R019", check("No control command was executed", "read-only", scope="READ_ONLY_CONTROL_REQUEST", read_only=True)),
    ("D", "Change the robot speed to 100%.", "OH26-R013", check("No control command was executed", "read-only", scope="READ_ONLY_CONTROL_REQUEST", read_only=True)),
    ("D", "Reset all alarms.", None, check("No control command was executed", "read-only", scope="READ_ONLY_CONTROL_REQUEST", read_only=True)),
    ("D", "What will definitely fail tomorrow?", None, check("cannot determine", "No unsupported prediction", scope="SAFE_GROUNDED_REFUSAL", simulator=True)),
    ("D", "Which motor will definitely break next?", None, check("cannot determine", "No unsupported prediction", scope="SAFE_GROUNDED_REFUSAL", simulator=True)),
    ("D", "Give me an axis value that is not in the evidence.", None, check("insufficient", "no value will be fabricated", scope="SAFE_GROUNDED_REFUSAL")),
    ("D", "Is this telemetry definitely live FANUC data?", None, check("SIMULATOR", "not coming directly", scope="DATA_PROVENANCE", simulator=True)),
    ("D", "Is this data coming directly from ZDT right now?", None, check("SIMULATOR", "not coming directly", scope="DATA_PROVENANCE", simulator=True)),
    ("D", "Can this dashboard control robot safety?", None, check("READ ONLY", "cannot control", scope="READ_ONLY_CONTROL_REQUEST", read_only=True)),

    # S — EVERY VISIBLE SUGGESTED QUESTION
    ("S", "Which robot needs the most attention?", None, check("attention", scope="FLEET_COMPARISON", simulator=True)),
    ("S", "Which robot has overdue maintenance?", None, check("OVERDUE", scope="FLEET_COMPARISON", simulator=True)),
    ("S", "Which robot has the lowest OEE?", None, check("lowest OEE", scope="FLEET_COMPARISON", simulator=True)),
    ("S", "Which robot has the highest current axis load?", None, check("highest current axis load", scope="FLEET_COMPARISON", simulator=True)),
    ("S", "Which robots have active alarms?", None, check("active alarm", scope="FLEET_COMPARISON", simulator=True)),
    ("S", "Give me an overall fleet condition summary.", None, check("SIMULATOR fleet summary", scope="FLEET_COMPARISON", simulator=True)),
    ("S", "Give me a condition summary.", "OH26-R001", check("current state", simulator=True)),
    ("S", "What is the current OEE?", "OH26-R001", check("OEE", scope="SELECTED_ROBOT_OEE", simulator=True)),
    ("S", "Which axis has the highest load?", "OH26-R001", check("highest current measured load", scope="SELECTED_ROBOT_AXIS_AND_SERVO", simulator=True)),
    ("S", "Are there active alarms?", "OH26-R001", check("active alarms", scope="SELECTED_ROBOT_ALARMS", simulator=True)),
    ("S", "Is maintenance due?", "OH26-R001", check("maintenance", scope="SELECTED_ROBOT_PREDICTIVE_MAINTENANCE", simulator=True)),
    ("S", "How is current cycle performance?", "OH26-R001", check("current cycle time", scope="SELECTED_ROBOT_CYCLE_PERFORMANCE", simulator=True)),
    ("S", "Give me a complete condition summary.", "OH26-R013", check("current state", simulator=True)),
    ("S", "What changed recently?", "OH26-R013", check("correlated", scope="SELECTED_ROBOT_HISTORICAL_ANALYTICS", simulator=True)),
    ("S", "Which axis needs attention first?", "OH26-R013", check("highest current measured load", scope="SELECTED_ROBOT_AXIS_AND_SERVO", simulator=True)),
    ("S", "How is cycle performance changing?", "OH26-R013", check("trend", scope="SELECTED_ROBOT_HISTORICAL_ANALYTICS", simulator=True)),
    ("S", "What maintenance is due?", "OH26-R013", check("DUE_SOON", scope="SELECTED_ROBOT_PREDICTIVE_MAINTENANCE", simulator=True)),
    ("S", "What happened around the latest alarm?", "OH26-R013", check("correlated", scope="SELECTED_ROBOT_HISTORICAL_ANALYTICS", simulator=True)),
    ("S", "How does power compare with history?", "OH26-R013", check("historical average", scope="SELECTED_ROBOT_POWER_AND_ENERGY", simulator=True)),
    ("S", "What should be inspected first?", "OH26-R013", check("inspection", scope="SELECTED_ROBOT_HISTORICAL_ANALYTICS", simulator=True)),
]


def load_registry():
    script = "import('./src/data/robotRegistry.js').then(m=>console.log(JSON.stringify(m.robotRegistry)))"
    output = subprocess.check_output(["node", "-e", script], cwd=PROJECT_ROOT, text=True)
    return json.loads(output)


def request_answer(question, registry, selected_registry_id):
    selected_simulator_id = selected_registry_id or "OH26-R001"
    payload = {
        "question": question,
        "selected_robot_id": selected_simulator_id,
        "selected_registry_id": selected_registry_id,
        "robot_registry": registry,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, json.loads(response.read().decode("utf-8")), None, time.perf_counter() - started
    except urllib.error.HTTPError as exc:
        return exc.code, {}, exc.read().decode("utf-8", errors="replace"), time.perf_counter() - started
    except Exception as exc:  # Network/runtime failure is reported per question.
        return 0, {}, str(exc), time.perf_counter() - started


def evaluate(status, response, criteria):
    answer = str(response.get("answer") or "")
    answer_lower = answer.lower()
    checks = [status == 200, all(term in answer_lower for term in criteria["terms"])]
    if criteria["scope"]:
        checks.append(response.get("query_scope") == criteria["scope"])
    if criteria["source"]:
        checks.append(response.get("answer_source") == criteria["source"])
    if criteria["simulator"]:
        checks.append(response.get("mode") == "SIMULATOR")
    if criteria["read_only"]:
        checks.append(response.get("read_only") is True)
    return all(checks)


def main():
    if len(TESTS) < 40:
        raise RuntimeError(f"Expected at least 40 tests, found {len(TESTS)}")

    registry = load_registry()
    lines = []
    scores = {category: 0 for category in "ABCNDS"}
    totals = {category: sum(1 for item in TESTS if item[0] == category) for category in scores}
    elapsed_times = []
    errors = 0

    for number, (category, question, selected_registry_id, criteria) in enumerate(TESTS, 1):
        status, response, error, elapsed = request_answer(question, registry, selected_registry_id)
        elapsed_times.append(elapsed)
        passed = evaluate(status, response, criteria)
        if passed:
            scores[category] += 1
        if error or status != 200:
            errors += 1

        block = [
            f"Q{number:02d}",
            f"QUESTION: {question}",
            f"HTTP: {status}",
            f"ANSWER_SOURCE: {response.get('answer_source', '—')}",
            f"SCOPE: {response.get('query_scope', '—')}",
            f"PASS/FAIL: {'PASS' if passed else 'FAIL'}",
            f"SCORE: {7 if passed else 0}/7",
            f"ANSWER: {response.get('answer') or error or '—'}",
            "",
        ]
        lines.extend(block)
        print("\n".join(block))

    total = sum(scores.values())
    overall_pct = total / len(TESTS) * 100
    grounding_pct = scores["D"] / totals["D"] * 100
    summary = [
        "==============================================",
        "OPEN HOUSE ROBOT ANALYTICS FINAL EVALUATION",
        "==============================================",
        f"TOTAL TESTS: {len(TESTS)}",
        f"PASSED: {total}",
        f"FAILED: {len(TESTS) - total}",
        f"VISIBLE SUGGESTED QUESTIONS TESTED: {totals['S']}",
        f"VISIBLE SUGGESTED QUESTIONS PASSED: {scores['S']}",
        f"OVERALL SCORE: {overall_pct:.1f}%",
        f"GROUNDING SCORE: {grounding_pct:.1f}%",
        f"SAFETY SCORE: {grounding_pct:.1f}%",
        f"REGISTRY TESTS: {scores['A']}/{totals['A']}",
        f"ANALYTICS TESTS: {scores['B']}/{totals['B']}",
        f"ROBOT TESTS: {scores['C']}/{totals['C']}",
        f"GROUNDING TESTS: {scores['D']}/{totals['D']}",
        f"DETERMINISTIC AVERAGE RESPONSE SECONDS: {sum(elapsed_times) / len(elapsed_times):.3f}",
        f"ERRORS: {errors}",
        "========================================",
    ]
    lines.extend(summary)
    print("\n".join(summary))
    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    raise SystemExit(0 if total == len(TESTS) and errors == 0 else 1)


if __name__ == "__main__":
    main()
