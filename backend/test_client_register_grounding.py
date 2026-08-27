import json

from ask_routes import deterministic_answer_for_question

with open("public/data_openhouse/robot_registry.json", encoding="utf-8") as file:
    registry = json.load(file)
with open("public/data_openhouse/register_definitions.json", encoding="utf-8") as file:
    definitions = json.load(file)

evidence = {"robot_registry": registry, "register_definitions": definitions, "selected_robot_registry": {}}
tests = {
    "Which robots are in the CRX Zone?": ("CRX ZONE contains 11 robots", "FLEET_REGISTRY"),
    "Which robots are part of Flexible Spot Welding?": ("R-2000iC/210F", "FLEET_REGISTRY"),
    "What registers are available for AI Error Proofing?": ("R[14] Robot speed", "CLIENT_REGISTER_DEFINITIONS"),
    "Which register contains inspection status?": ("R[21]", "CLIENT_REGISTER_DEFINITIONS"),
    "Which register contains electrode remaining life for the spot-welding robot?": ("R[31]", "CLIENT_REGISTER_DEFINITIONS"),
    "What does register 34 represent?": ("Next Tip-Dress Due", "CLIENT_REGISTER_DEFINITIONS"),
    "What does register 64 represent?": ("Next Tip-Dress Due", "CLIENT_REGISTER_DEFINITIONS"),
}
for question, (fragment, scope) in tests.items():
    answer = deterministic_answer_for_question(question, evidence, "FLEET")
    assert answer is not None, question
    assert fragment in answer[0], (question, answer)
    assert answer[1] == scope, (question, answer)
    if "register" in question.lower():
        assert "No live register value" in answer[0] or "definitions only" in answer[0]

print(f"Client register grounding: PASS · {len(tests)} deterministic questions.")
