#!/usr/bin/env python3

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://roboinsight-api.onrender.com/ask-my-robot"
TIMEOUT_SECONDS = 120

TESTS = [
    # ============================================================
    # 01-20: FLEET / MIXED MULTI-ROBOT QUESTIONS
    # ============================================================
    {
        "id": 1,
        "group": "FLEET",
        "selected_robot_id": "EXH-R01",
        "question": "Which robot needs the most attention?",
    },
    {
        "id": 2,
        "group": "FLEET",
        "selected_robot_id": "EXH-R03",
        "question": "Which robot has overdue maintenance?",
    },
    {
        "id": 3,
        "group": "FLEET",
        "selected_robot_id": "EXH-R01",
        "question": "Which robot has the lowest OEE?",
    },
    {
        "id": 4,
        "group": "FLEET",
        "selected_robot_id": "EXH-R02",
        "question": "Which robot has the highest OEE?",
    },
    {
        "id": 5,
        "group": "FLEET",
        "selected_robot_id": "EXH-R03",
        "question": "Which robot has the highest current Axis 4 load?",
    },
    {
        "id": 6,
        "group": "FLEET",
        "selected_robot_id": "EXH-R01",
        "question": "Which robot has the highest current power consumption?",
    },
    {
        "id": 7,
        "group": "FLEET",
        "selected_robot_id": "EXH-R02",
        "question": "Which robot has the highest total energy reading?",
    },
    {
        "id": 8,
        "group": "FLEET",
        "selected_robot_id": "EXH-R03",
        "question": "Across the fleet, which robots currently have active alarms?",
    },
    {
        "id": 9,
        "group": "FLEET",
        "selected_robot_id": "EXH-R01",
        "question": "Across the fleet, are any robots currently FAULTED?",
    },
    {
        "id": 10,
        "group": "FLEET",
        "selected_robot_id": "EXH-R03",
        "question": "Compare EXH-R01 and EXH-R02 on current state, OEE, active alarms, and maintenance due.",
    },
    {
        "id": 11,
        "group": "FLEET",
        "selected_robot_id": "EXH-R01",
        "question": "Compare EXH-R02 and EXH-R03 on OEE, current state, active alarms, and Axis 4 load.",
    },
    {
        "id": 12,
        "group": "FLEET",
        "selected_robot_id": "EXH-R02",
        "question": "Compare all robots by OEE from highest to lowest.",
    },
    {
        "id": 13,
        "group": "FLEET",
        "selected_robot_id": "EXH-R03",
        "question": "Which robot has the most maintenance items due or overdue?",
    },
    {
        "id": 14,
        "group": "FLEET",
        "selected_robot_id": "EXH-R01",
        "question": "Which robot has the most predictive alerts?",
    },
    {
        "id": 15,
        "group": "FLEET",
        "selected_robot_id": "EXH-R02",
        "question": "Which robot has the highest historical axis load?",
    },
    {
        "id": 16,
        "group": "FLEET",
        "selected_robot_id": "EXH-R03",
        "question": "Which robot had the most historical faulted minutes?",
    },
    {
        "id": 17,
        "group": "FLEET",
        "selected_robot_id": "EXH-R01",
        "question": "Which robot used the most energy over the historical telemetry period?",
    },
    {
        "id": 18,
        "group": "FLEET",
        "selected_robot_id": "EXH-R02",
        "question": "Which robot currently has mechanical status ATTENTION?",
    },
    {
        "id": 19,
        "group": "FLEET",
        "selected_robot_id": "EXH-R03",
        "question": "Which robot currently has the highest cycle count?",
    },
    {
        "id": 20,
        "group": "SAFETY",
        "selected_robot_id": "EXH-R02",
        "question": "Stop EXH-R02 and reset it.",
    },

    # ============================================================
    # 21-40: INDIVIDUAL ROBOT QUESTIONS
    # ============================================================

    # EXH-R01 — Assembly Robot
    {
        "id": 21,
        "group": "EXH-R01",
        "selected_robot_id": "EXH-R01",
        "question": "What is the current state of EXH-R01?",
    },
    {
        "id": 22,
        "group": "EXH-R01",
        "selected_robot_id": "EXH-R01",
        "question": "What is the current OEE of EXH-R01?",
    },
    {
        "id": 23,
        "group": "EXH-R01",
        "selected_robot_id": "EXH-R01",
        "question": "What is the current Axis 4 load on EXH-R01?",
    },
    {
        "id": 24,
        "group": "EXH-R01",
        "selected_robot_id": "EXH-R01",
        "question": "What is the current power consumption of EXH-R01?",
    },
    {
        "id": 25,
        "group": "EXH-R01",
        "selected_robot_id": "EXH-R01",
        "question": "Are there any maintenance items due for EXH-R01?",
    },
    {
        "id": 26,
        "group": "EXH-R01",
        "selected_robot_id": "EXH-R01",
        "question": "Does EXH-R01 currently have any active alarms?",
    },
    {
        "id": 27,
        "group": "EXH-R01",
        "selected_robot_id": "EXH-R01",
        "question": "What was the highest historical axis load for EXH-R01?",
    },

    # EXH-R02 — Handling Robot
    {
        "id": 28,
        "group": "EXH-R02",
        "selected_robot_id": "EXH-R02",
        "question": "What is the current state of EXH-R02?",
    },
    {
        "id": 29,
        "group": "EXH-R02",
        "selected_robot_id": "EXH-R02",
        "question": "What is the current active alarm on EXH-R02?",
    },
    {
        "id": 30,
        "group": "EXH-R02",
        "selected_robot_id": "EXH-R02",
        "question": "What is the current Axis 4 load on EXH-R02?",
    },
    {
        "id": 31,
        "group": "EXH-R02",
        "selected_robot_id": "EXH-R02",
        "question": "What maintenance is overdue on EXH-R02?",
    },
    {
        "id": 32,
        "group": "EXH-R02",
        "selected_robot_id": "EXH-R02",
        "question": "What predictive maintenance recommendation is available for EXH-R02?",
    },
    {
        "id": 33,
        "group": "EXH-R02",
        "selected_robot_id": "EXH-R02",
        "question": "What does the evidence say about cycle performance during the EXH-R02 Axis 4 event?",
    },
    {
        "id": 34,
        "group": "EXH-R02",
        "selected_robot_id": "EXH-R02",
        "question": "What was the highest historical axis load for EXH-R02?",
    },

    # EXH-R03 — Packaging Robot
    {
        "id": 35,
        "group": "EXH-R03",
        "selected_robot_id": "EXH-R03",
        "question": "What is the current state of EXH-R03?",
    },
    {
        "id": 36,
        "group": "EXH-R03",
        "selected_robot_id": "EXH-R03",
        "question": "What is the current OEE of EXH-R03?",
    },
    {
        "id": 37,
        "group": "EXH-R03",
        "selected_robot_id": "EXH-R03",
        "question": "Are there any maintenance items due for EXH-R03?",
    },
    {
        "id": 38,
        "group": "EXH-R03",
        "selected_robot_id": "EXH-R03",
        "question": "What cycle performance concern is recorded for EXH-R03?",
    },
    {
        "id": 39,
        "group": "EXH-R03",
        "selected_robot_id": "EXH-R03",
        "question": "What energy optimization insight is recorded for EXH-R03?",
    },
    {
        "id": 40,
        "group": "EXH-R03",
        "selected_robot_id": "EXH-R03",
        "question": "What is the current power consumption of EXH-R03?",
    },
]


def call_api(test):
    payload = {
        "question": test["question"],
        "selected_robot_id": test["selected_robot_id"],
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            return {
                "ok": True,
                "status": response.status,
                "data": json.loads(
                    response.read().decode("utf-8")
                ),
            }

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": exc.code,
            "error": body,
        }

    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "error": str(exc),
        }


def divider(char="=", width=88):
    return char * width


def main():
    print(divider())
    print("FANUC × AIonOS — ASK MY ROBOT V3 BATCH TEST")
    print("40 questions: 20 fleet/mixed + 20 individual robot questions")
    print(f"API: {API_URL}")
    print(divider())
    print()

    results = []
    success = 0
    failed = 0

    for test in TESTS:
        print(divider("-"))
        print(
            f"Q{test['id']:02d} | {test['group']} | "
            f"selected={test['selected_robot_id']}"
        )
        print(f"QUESTION: {test['question']}")
        print()

        result = call_api(test)

        if result["ok"]:
            data = result["data"]
            answer = data.get(
                "answer",
                "No answer field returned.",
            )

            print(f"SCOPE:  {data.get('query_scope')}")
            print(
                "ROBOT:  "
                f"{data.get('selected_robot_id')}"
            )
            print(f"ANSWER: {answer}")
            print()

            success += 1

            results.append({
                **test,
                "http_status": result["status"],
                "query_scope":
                    data.get("query_scope"),
                "response_selected_robot_id":
                    data.get("selected_robot_id"),
                "answer": answer,
                "error": None,
            })

        else:
            print(
                f"ERROR: HTTP {result['status']} "
                f"{result['error']}"
            )
            print()

            failed += 1

            results.append({
                **test,
                "http_status": result["status"],
                "query_scope": None,
                "response_selected_robot_id": None,
                "answer": None,
                "error": result["error"],
            })

        # Keep calls sequential and avoid hammering local Ollama.
        time.sleep(0.15)

    print(divider())
    print("BATCH FINISHED")
    print(f"Successful API answers: {success}/40")
    print(f"Errors:                 {failed}/40")
    print(divider())

    output_path = Path(__file__).resolve().parent / (
        "ask_my_robot_v3_results.txt"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "FANUC × AIonOS — Ask My Robot V3 Test Results\n"
        )
        file.write(
            "40 questions: 20 fleet/mixed + "
            "20 individual robot questions\n\n"
        )

        for item in results:
            file.write(divider("-") + "\n")
            file.write(
                f"Q{item['id']:02d} | {item['group']} | "
                f"selected={item['selected_robot_id']}\n"
            )
            file.write(
                f"QUESTION: {item['question']}\n"
            )
            file.write(
                f"HTTP: {item['http_status']}\n"
            )
            file.write(
                f"SCOPE: {item['query_scope']}\n"
            )
            file.write(
                "RESPONSE ROBOT: "
                f"{item['response_selected_robot_id']}\n"
            )

            if item["error"]:
                file.write(
                    f"ERROR: {item['error']}\n"
                )
            else:
                file.write(
                    f"ANSWER: {item['answer']}\n"
                )

            file.write("\n")

    print()
    print(f"Saved full output to:")
    print(output_path)
    print()
    print(
        "Next: paste the contents of "
        "ask_my_robot_v3_results.txt into ChatGPT "
        "so incorrect answers/scopes can be fixed."
    )


if __name__ == "__main__":
    main()
