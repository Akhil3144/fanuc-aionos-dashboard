#!/usr/bin/env python3
"""Exercise the 20 handover prompts and enforce intent/answer diversity."""

import argparse
import re
from difflib import SequenceMatcher

import ask_routes
from ask_routes import AskRobotRequest, ask_my_robot


CASES = [
    ("OH26-R013", "ROBOT", "Give me a complete condition summary of this robot."),
    ("OH26-R013", "ROBOT", "What changed recently, and which changes deserve the most attention?"),
    ("OH26-R013", "ROBOT", "What should an engineer inspect first, and why?"),
    ("OH26-R013", "ROBOT", "Explain the latest alarm in the context of recent robot performance."),
    ("OH26-R013", "ROBOT", "Analyze the relationship between the recent cycle-time increase and Axis 4 load trend."),
    ("OH26-R013", "ROBOT", "Based on the available evidence, what are the three biggest operational concerns for this robot?"),
    ("OH26-R013", "ROBOT", "Summarize the robot's production, health, maintenance, alarms, axis condition, and energy usage in one assessment."),
    ("OH26-R013", "ROBOT", "If you were the maintenance engineer reviewing this robot, what would you investigate during the next maintenance window?"),
    ("OH26-R013", "ROBOT", "Compare the robot's current condition with its recent historical behavior and explain the important differences."),
    ("OH26-R013", "ROBOT", "Does the available evidence suggest that the robot's condition is improving, stable, or degrading? Explain your reasoning."),
    ("OH26-R019", "ROBOT", "Give me an engineering assessment of this robot's current condition."),
    ("OH26-R019", "ROBOT", "Explain why this robot currently requires attention."),
    ("OH26-R019", "ROBOT", "Analyze its power consumption, axis loading, servo events, alarms, and maintenance status together."),
    ("OH26-R019", "ROBOT", "What happened around the latest alarm, and what evidence should an engineer investigate?"),
    ("OH26-R019", "ROBOT", "What is the most important maintenance risk for this robot and why?"),
    ("OH26-R013", "FLEET", "Give me an executive summary of the overall fleet condition."),
    ("OH26-R013", "FLEET", "Which operational risks across the fleet deserve management attention first, and why?"),
    ("OH26-R013", "FLEET", "Identify the most concerning robots and explain the evidence behind your ranking."),
    ("OH26-R013", "FLEET", "Summarize the main performance, maintenance, alarm, and energy patterns across the fleet."),
    ("OH26-R013", "FLEET", "If maintenance resources are limited, how should the current robot inspections be prioritized based only on the available evidence?"),
]


def normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ollama-off", action="store_true", help="force the deterministic AI fallback")
    mode.add_argument("--ollama-on", action="store_true", help="call the real configured Ollama service")
    args = parser.parse_args()
    original = ask_routes.ask_ollama
    if args.ollama_off:
        ask_routes.ask_ollama = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("test offline"))
    results = []
    try:
        for number, (robot_id, scope, question) in enumerate(CASES, 1):
            response = ask_my_robot(AskRobotRequest(question=question, robot_id=robot_id, selected_robot_id=robot_id, scope=scope))
            results.append(response)
            print(f"Q{number:02d}\nQUESTION: {question}\nINTENT: {response['intent']}\nRESOLUTION_MODE: {response['resolution_mode']}\nOLLAMA_CALLED: {'YES' if response['resolution_mode'] == 'AI' else 'NO'}\nANSWER: {response['answer']}\n")
    finally:
        ask_routes.ask_ollama = original

    duplicates = []
    maximum = (0.0, None)
    for left in range(len(results)):
        for right in range(left + 1, len(results)):
            ratio = SequenceMatcher(None, normalized(results[left]["answer"]), normalized(results[right]["answer"])).ratio()
            if ratio > maximum[0]:
                maximum = (ratio, (left + 1, right + 1))
            if results[left]["intent"] != results[right]["intent"] and ratio > 0.85:
                duplicates.append((left + 1, right + 1, ratio))

    expected_unique = 17
    passed = len(results) == 20 and len({item["intent"] for item in results}) == expected_unique and not duplicates
    print(f"QUESTIONS: {len(results)}/20")
    print(f"UNIQUE_INTENTS: {len({item['intent'] for item in results})}/{expected_unique}")
    print(f"MAX_SIMILARITY: {maximum[0]:.3f} (Q{maximum[1][0]:02d}/Q{maximum[1][1]:02d})")
    print(f"DUPLICATES_OVER_85_PERCENT: {len(duplicates)}")
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
