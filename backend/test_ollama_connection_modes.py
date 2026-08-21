#!/usr/bin/env python3
"""Verify real Ollama calls, deterministic bypass, and offline fallbacks."""

import argparse
import time

import ask_routes
from ask_routes import AskRobotRequest, ask_my_robot


COMPLEX = [
    ("ROBOT", "What changed recently, and which changes deserve the most attention?"),
    ("ROBOT", "What should an engineer inspect first, and why?"),
    ("ROBOT", "Based on the available evidence, what are the three biggest operational concerns for this robot?"),
    ("ROBOT", "Compare the robot's current condition with its recent historical behavior and explain the important differences."),
    ("FLEET", "Give me an executive summary of the overall fleet condition."),
]

SIMPLE = [
    "What is the current OEE?",
    "Which axis has the highest load?",
    "Are there active alarms?",
    "What maintenance is due?",
    "What is current power?",
]


def request(question, scope="ROBOT"):
    return ask_my_robot(AskRobotRequest(
        question=question,
        robot_id="OH26-R013",
        selected_robot_id="OH26-R013",
        selected_registry_id="OH26-R013",
        scope=scope,
    ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama-on", action="store_true", help="run five calls against real local Ollama")
    args = parser.parse_args()

    original = ask_routes.ask_ollama
    calls = 0

    def counted(question, evidence):
        nonlocal calls
        calls += 1
        return original(question, evidence)

    if args.ollama_on:
        ask_routes.ask_ollama = counted
        latencies = []
        results = []
        try:
            for number, (scope, question) in enumerate(COMPLEX, 1):
                started = time.perf_counter()
                response = request(question, scope)
                latencies.append(time.perf_counter() - started)
                results.append(response)
                print(f"AI{number}: {response['resolution_mode']} | {latencies[-1]:.3f}s | {response['intent']}\n{response['answer']}\n")
        finally:
            ask_routes.ask_ollama = original
        passed = sum(item["resolution_mode"] == "AI" for item in results)
        print(f"OLLAMA_CALLED: {calls}/5")
        print(f"OLLAMA_SUCCESS: {passed}/5")
        print(f"FIRST_AI_LATENCY: {latencies[0]:.3f}s")
        print(f"SUBSEQUENT_AVG: {sum(latencies[1:]) / 4:.3f}s")
        raise SystemExit(0 if calls == passed == 5 else 1)

    simple_calls = 0
    def forbidden(*_args, **_kwargs):
        nonlocal simple_calls
        simple_calls += 1
        raise AssertionError("simple question reached Ollama")
    ask_routes.ask_ollama = forbidden
    try:
        deterministic = [request(question) for question in SIMPLE]
    finally:
        ask_routes.ask_ollama = original

    ask_routes.ask_ollama = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("simulated unavailable"))
    try:
        fallback = [request(question, scope) for scope, question in COMPLEX]
    finally:
        ask_routes.ask_ollama = original

    deterministic_passed = sum(item["resolution_mode"] == "DETERMINISTIC" for item in deterministic)
    fallback_passed = sum(item["resolution_mode"] == "AI_FALLBACK" and bool(item["answer"]) for item in fallback)
    print(f"DETERMINISTIC_FAST_PATH: {deterministic_passed}/5")
    print(f"DETERMINISTIC_OLLAMA_CALLS: {simple_calls}")
    print(f"OLLAMA_OFF_FALLBACK: {fallback_passed}/5")
    raise SystemExit(0 if deterministic_passed == fallback_passed == 5 and simple_calls == 0 else 1)


if __name__ == "__main__":
    main()
