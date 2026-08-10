from __future__ import annotations

import json
import re
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ollama_client import ask_ollama, OLLAMA_MODEL


# ============================================================
# PATHS — SYNTHETIC DATA V3
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "public" / "data_v3"

TELEMETRY_FILE = DATA_DIR / "telemetry_history.jsonl"
FLEET_LATEST_FILE = DATA_DIR / "fleet_latest_snapshot.json"
ALARMS_FILE = DATA_DIR / "alarms.json"
MAINTENANCE_FILE = DATA_DIR / "maintenance.json"
INSIGHTS_FILE = DATA_DIR / "derived_insights.json"
DATA_DICTIONARY_FILE = DATA_DIR / "data_dictionary.json"


# ============================================================
# TIMEZONE
# ============================================================

UTC = timezone.utc
IST = ZoneInfo("Asia/Kolkata")


def to_ist(value):
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)

    return value.astimezone(IST).isoformat()


# ============================================================
# ROUTER / REQUEST
# ============================================================

router = APIRouter(tags=["Ask My Robot"])


class AskRobotRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=2,
        max_length=500,
    )

    # Current selected robot snapshot from React.
    live_snapshot: dict | None = None

    # Optional explicit selected robot id.
    selected_robot_id: str | None = None


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path: Path):
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_dictionary_field(data, field_name: str):
    if isinstance(data, dict):
        if data.get("field") == field_name:
            return data

        for value in data.values():
            found = find_dictionary_field(value, field_name)
            if found is not None:
                return found

    elif isinstance(data, list):
        for item in data:
            found = find_dictionary_field(item, field_name)
            if found is not None:
                return found

    return None


def load_fleet():
    fleet = load_json(FLEET_LATEST_FILE) or {}
    robots = fleet.get("robots", [])

    if not isinstance(robots, list) or not robots:
        raise RuntimeError(
            "fleet_latest_snapshot.json contains no robots"
        )

    return fleet, robots


def robot_by_id(robots, robot_id):
    return next(
        (
            robot
            for robot in robots
            if robot.get("robot_id") == robot_id
        ),
        None,
    )


def normalize_robot_id(value):
    if not value:
        return None

    match = re.search(
        r"\bEXH[-_ ]?R0?([1-9])\b",
        str(value).upper(),
    )

    if not match:
        return None

    return f"EXH-R0{match.group(1)}"


def robot_ids_in_question(question):
    ids = []

    for match in re.finditer(
        r"\bEXH[-_ ]?R0?([1-9])\b",
        question.upper(),
    ):
        robot_id = f"EXH-R0{match.group(1)}"

        if robot_id not in ids:
            ids.append(robot_id)

    aliases = {
        "assembly robot": "EXH-R01",
        "assembly": "EXH-R01",
        "handling robot": "EXH-R02",
        "handling": "EXH-R02",
        "packaging robot": "EXH-R03",
        "packaging": "EXH-R03",
    }

    q = question.lower()

    for alias, robot_id in aliases.items():
        if alias in q and robot_id not in ids:
            ids.append(robot_id)

    return ids


# ============================================================
# SNAPSHOT -> STRUCTURED STATE
# ============================================================

def build_state(snapshot):
    if not snapshot:
        return {}

    live_cell = snapshot.get("live_cell", {})
    production = snapshot.get("production", {})
    robot_status = snapshot.get("robot_status", {})
    alarms = snapshot.get("alarms", {})
    power_data = snapshot.get("power_data", {})
    kpis = snapshot.get("derived_kpis", {})

    axis_status = [
        {
            "axis": axis.get("axis"),
            "load_pct": axis.get("axis_load_pct"),
            "error_count": axis.get("error_count"),
            "servo_indicator": axis.get("servo_indicator"),
        }
        for axis in snapshot.get("axis_servo", [])
    ]

    return {
        "robot_id": snapshot.get("robot_id"),
        "robot_name": snapshot.get("robot_name"),
        "display_name": snapshot.get("display_name"),
        "role": snapshot.get("role"),
        "timestamp": snapshot.get("timestamp"),
        "source_mode": snapshot.get("source_mode"),
        "shift": snapshot.get("shift"),

        "robot_state": live_cell.get("state"),

        "cycle_count_total": production.get(
            "cycle_count_total"
        ),
        "current_cycle_time_s": production.get(
            "actual_cycle_time_s"
        ),
        "target_cycle_time_s": production.get(
            "target_cycle_time_s"
        ),
        "running_rate": production.get("running_rate"),

        "availability_pct": kpis.get(
            "shift_availability_pct"
        ),
        "performance_pct": kpis.get(
            "shift_performance_pct"
        ),
        "quality_pct": kpis.get(
            "shift_quality_pct"
        ),
        "oee_pct": kpis.get("shift_oee_pct"),

        "working_status": robot_status.get(
            "working_status"
        ),
        "process_status": robot_status.get(
            "process_status"
        ),
        "mechanical_status": robot_status.get(
            "mechanical_status"
        ),

        "active_alarm_count": alarms.get(
            "active_alarm_count",
            0,
        ),
        "active_alarm_ids": alarms.get(
            "active_alarm_ids",
            [],
        ),

        "current_power_kw": power_data.get(
            "instantaneous_kw"
        ),
        "total_energy_kwh": power_data.get(
            "kwh_total"
        ),

        "axis_status": axis_status,
    }


# ============================================================
# DUCKDB HISTORICAL ANALYTICS
# ============================================================

def _telemetry_source():
    if not TELEMETRY_FILE.exists():
        raise RuntimeError(
            "data_v3/telemetry_history.jsonl not found"
        )

    return (
        TELEMETRY_FILE
        .as_posix()
        .replace("'", "''")
    )


def build_robot_historical_evidence(robot_id):
    source = _telemetry_source()
    safe_robot = robot_id.replace("'", "''")

    con = duckdb.connect(database=":memory:")

    try:
        summary = con.execute(
            f"""
            SELECT
                COUNT(*) AS records,
                MIN(timestamp),
                MAX(timestamp),

                SUM(
                    production.cycles_completed_this_minute
                ) AS cycles_completed,

                ROUND(
                    AVG(
                        CASE
                            WHEN production.actual_cycle_time_s > 0
                            THEN production.actual_cycle_time_s
                        END
                    ),
                    2
                ) AS average_cycle_time_s,

                ROUND(
                    MAX(production.actual_cycle_time_s),
                    2
                ) AS maximum_cycle_time_s,

                COUNT(*) FILTER (
                    WHERE live_cell.state = 'FAULTED'
                ) AS faulted_minutes,

                ROUND(
                    MAX(power_data.kwh_total)
                    - MIN(power_data.kwh_total),
                    2
                ) AS energy_used_kwh,

                ROUND(
                    AVG(power_data.instantaneous_kw),
                    2
                ) AS average_power_kw,

                ROUND(
                    MAX(power_data.instantaneous_kw),
                    2
                ) AS peak_power_kw

            FROM read_ndjson_auto('{source}')
            WHERE robot_id = '{safe_robot}'
            """
        ).fetchone()

        highest_axis = con.execute(
            f"""
            SELECT
                axis_data.axis,
                ROUND(
                    MAX(axis_data.axis_load_pct),
                    2
                ) AS max_load_pct

            FROM
                read_ndjson_auto('{source}') AS telemetry,
                UNNEST(
                    telemetry.axis_servo
                ) AS axis_table(axis_data)

            WHERE telemetry.robot_id = '{safe_robot}'

            GROUP BY axis_data.axis
            ORDER BY max_load_pct DESC
            LIMIT 1
            """
        ).fetchone()

        return {
            "robot_id": robot_id,

            "full_history": {
                "records": summary[0],
                "start_time": to_ist(summary[1]),
                "end_time": to_ist(summary[2]),
                "cycles_completed": summary[3],
                "average_cycle_time_s": summary[4],
                "maximum_cycle_time_s": summary[5],
                "faulted_minutes": summary[6],
                "energy_used_kwh": summary[7],
                "average_power_kw": summary[8],
                "peak_power_kw": summary[9],
            },

            "highest_historical_axis_load": {
                "axis": (
                    highest_axis[0]
                    if highest_axis
                    else None
                ),
                "load_pct": (
                    highest_axis[1]
                    if highest_axis
                    else None
                ),
                "measurement_type":
                    "historical maximum",
            },
        }

    finally:
        con.close()


def build_fleet_historical_evidence():
    source = _telemetry_source()

    con = duckdb.connect(database=":memory:")

    try:
        robot_rows = con.execute(
            f"""
            SELECT
                robot_id,

                SUM(
                    production.cycles_completed_this_minute
                ) AS cycles_completed,

                ROUND(
                    AVG(
                        CASE
                            WHEN production.actual_cycle_time_s > 0
                            THEN production.actual_cycle_time_s
                        END
                    ),
                    2
                ) AS average_cycle_time_s,

                COUNT(*) FILTER (
                    WHERE live_cell.state = 'FAULTED'
                ) AS faulted_minutes,

                ROUND(
                    MAX(power_data.kwh_total)
                    - MIN(power_data.kwh_total),
                    2
                ) AS energy_used_kwh,

                ROUND(
                    MAX(power_data.instantaneous_kw),
                    2
                ) AS peak_power_kw

            FROM read_ndjson_auto('{source}')

            GROUP BY robot_id
            ORDER BY robot_id
            """
        ).fetchall()

        axis_rows = con.execute(
            f"""
            SELECT
                telemetry.robot_id,
                axis_data.axis,
                ROUND(
                    MAX(axis_data.axis_load_pct),
                    2
                ) AS max_load_pct

            FROM
                read_ndjson_auto('{source}') AS telemetry,
                UNNEST(
                    telemetry.axis_servo
                ) AS axis_table(axis_data)

            GROUP BY
                telemetry.robot_id,
                axis_data.axis

            ORDER BY
                telemetry.robot_id,
                max_load_pct DESC
            """
        ).fetchall()

        highest_by_robot = {}

        for robot_id, axis, load in axis_rows:
            if robot_id not in highest_by_robot:
                highest_by_robot[robot_id] = {
                    "axis": axis,
                    "load_pct": load,
                }

        return {
            "robots": [
                {
                    "robot_id": row[0],
                    "cycles_completed": row[1],
                    "average_cycle_time_s": row[2],
                    "faulted_minutes": row[3],
                    "energy_used_kwh": row[4],
                    "peak_power_kw": row[5],
                    "highest_historical_axis_load":
                        highest_by_robot.get(
                            row[0],
                            {},
                        ),
                }
                for row in robot_rows
            ]
        }

    finally:
        con.close()


# ============================================================
# FLEET SUMMARY
# ============================================================

def build_fleet_summary(
    robots,
    maintenance,
    insights,
):
    output = []

    for snapshot in robots:
        robot_id = snapshot.get("robot_id")
        state = build_state(snapshot)

        robot_maintenance = [
            item
            for item in maintenance
            if item.get("robot_id") == robot_id
        ]

        due_items = [
            item
            for item in robot_maintenance
            if item.get("status") in {
                "OVERDUE",
                "DUE_SOON",
            }
        ]

        robot_insights = [
            item
            for item in insights
            if (
                item.get("robot_id") == robot_id
                and item.get("category")
                != "CONNECTIVITY"
            )
        ]

        predictive = [
            item
            for item in robot_insights
            if item.get("category") in {
                "PREDICTIVE_MAINTENANCE",
                "ANOMALY",
            }
        ]

        axes = state.get("axis_status", [])

        highest_current_axis = (
            max(
                axes,
                key=lambda item:
                    item.get("load_pct") or 0,
            )
            if axes
            else {}
        )

        axis4 = next(
            (
                item
                for item in axes
                if item.get("axis") == 4
            ),
            {},
        )

        output.append({
            "robot_id": robot_id,
            "robot_name": state.get("robot_name"),
            "display_name": state.get("display_name"),
            "role": state.get("role"),

            "robot_state": state.get("robot_state"),
            "mechanical_status":
                state.get("mechanical_status"),

            "oee_pct": state.get("oee_pct"),
            "cycle_count_total":
                state.get("cycle_count_total"),
            "current_cycle_time_s":
                state.get("current_cycle_time_s"),

            "active_alarm_count":
                state.get("active_alarm_count"),
            "active_alarm_ids":
                state.get("active_alarm_ids"),

            "maintenance_due_count":
                len(due_items),
            "maintenance_due_items":
                due_items,

            "predictive_alert_count":
                len(predictive),

            "current_power_kw":
                state.get("current_power_kw"),
            "total_energy_kwh":
                state.get("total_energy_kwh"),

            "axis_4_current_load_pct":
                axis4.get("load_pct"),

            "highest_current_axis":
                highest_current_axis,
        })

    return output


# ============================================================
# COMPLETE EVIDENCE PACKAGE
# ============================================================

def build_evidence(
    live_snapshot=None,
    selected_robot_id=None,
):
    fleet, robots = load_fleet()

    alarms = load_json(ALARMS_FILE) or []
    maintenance = load_json(MAINTENANCE_FILE) or []
    insights = load_json(INSIGHTS_FILE) or []
    data_dictionary = (
        load_json(DATA_DICTIONARY_FILE)
        or {}
    )

    requested_id = normalize_robot_id(
        selected_robot_id
    )

    if not requested_id and live_snapshot:
        requested_id = normalize_robot_id(
            live_snapshot.get("robot_id")
        )

    if not requested_id:
        requested_id = robots[0].get("robot_id")

    selected_latest = robot_by_id(
        robots,
        requested_id,
    )

    if selected_latest is None:
        raise RuntimeError(
            f"Robot {requested_id} was not found "
            "in the V3 fleet dataset."
        )

    current_snapshot = (
        live_snapshot
        if (
            live_snapshot
            and live_snapshot.get("robot_id")
            == requested_id
        )
        else selected_latest
    )

    selected_alarms = [
        alarm
        for alarm in alarms
        if alarm.get("robot_id") == requested_id
    ]

    selected_maintenance = [
        item
        for item in maintenance
        if item.get("robot_id") == requested_id
    ]

    selected_insights = [
        item
        for item in insights
        if (
            item.get("robot_id") == requested_id
            and item.get("category")
            != "CONNECTIVITY"
        )
    ]

    return {
        "evidence_type":
            "calculated_multi_robot_evidence",

        "system_mode": "READ_ONLY",

        "selected_robot_id": requested_id,

        "current_state":
            build_state(current_snapshot),

        # In the static simulator, current selected snapshot
        # and the V3 fleet latest snapshot are the two reference
        # states. There is no 1-second replay in the UI.
        "selected_robot_latest_state":
            build_state(selected_latest),

        "selected_robot_historical_analytics":
            build_robot_historical_evidence(
                requested_id
            ),

        "selected_robot_alarm_history":
            selected_alarms,

        "selected_robot_maintenance":
            selected_maintenance,

        "selected_robot_insights":
            selected_insights,

        "fleet_summary":
            build_fleet_summary(
                robots,
                maintenance,
                insights,
            ),

        "fleet_historical_analytics":
            build_fleet_historical_evidence(),

        "all_alarms": alarms,
        "all_maintenance": maintenance,
        "all_insights": [
            item
            for item in insights
            if item.get("category")
            != "CONNECTIVITY"
        ],

        "data_dictionary":
            data_dictionary,

        "important_interpretation_rules": [
            (
                "The dashboard is a static simulator "
                "snapshot. Values change only when the "
                "user selects another robot."
            ),
            (
                "Always distinguish the selected robot "
                "from fleet-level comparisons."
            ),
            (
                "Historical maximum values are not "
                "current values."
            ),
            (
                "Correlation between events does not "
                "prove root cause."
            ),
            (
                "Maintenance recommendations may only "
                "be stated when supported by supplied "
                "maintenance or AI insight evidence."
            ),
            (
                "The dashboard is READ_ONLY and cannot "
                "execute robot control commands."
            ),
            (
                "Connectivity is not presented as an "
                "AI insight in this exhibition view."
            ),
        ],
    }


# ============================================================
# QUESTION SCOPE HELPERS
# ============================================================

def is_control_request(question):
    q = question.lower().strip()

    if re.search(
        r"^(please\s+)?(stop|start|reset|jog|move)\b",
        q,
    ):
        return True

    control_terms = (
        "change speed",
        "reduce speed",
        "increase speed",
        "change override",
        "set override",
        "write register",
        "modify io",
        "modify i/o",
        "change io",
        "change i/o",
    )

    return any(term in q for term in control_terms)


def is_fleet_question(question):
    q = question.lower()
    ids = robot_ids_in_question(question)

    if len(ids) >= 2:
        return True

    fleet_terms = (
        "which robot",
        "which robots",
        "which one",
        "all robots",
        "all the robots",
        "fleet",
        "compare robots",
        "compare the robots",
        "among the robots",
        "across robots",
        "across the robots",
        "across the fleet",
        "most attention",
        "least oee",
        "lowest oee",
        "highest oee",
        "most energy",
        "highest energy",
        "highest power",
        "highest axis",
        "highest load",
        "most maintenance",
        "most predictive",
    )

    return any(term in q for term in fleet_terms)


def _fmt(value):
    if value is None:
        return "—"

    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")

    return str(value)


def _robot_label(item):
    robot_id = item.get("robot_id") or "UNKNOWN"
    name = (
        item.get("display_name")
        or item.get("robot_name")
    )

    if name:
        return f"{robot_id} ({name})"

    return robot_id


def deterministic_answer_for_question(
    question,
    evidence,
):
    """
    Exact-answer layer for factual V3 simulator questions.

    Deterministic analytics owns ranking, comparisons and direct
    lookups. Ollama is reserved for open-ended grounded explanation.
    """
    q = question.lower().strip()

    fleet = evidence.get("fleet_summary", []) or []
    fleet_history = (
        evidence.get(
            "fleet_historical_analytics",
            {},
        ).get("robots", [])
        or []
    )

    current = evidence.get("current_state", {}) or {}
    historical = evidence.get(
        "selected_robot_historical_analytics",
        {},
    ) or {}

    alarms = evidence.get(
        "selected_robot_alarm_history",
        [],
    ) or []

    maintenance = evidence.get(
        "selected_robot_maintenance",
        [],
    ) or []

    insights = evidence.get(
        "selected_robot_insights",
        [],
    ) or []

    all_maintenance = evidence.get(
        "all_maintenance",
        [],
    ) or []

    # --------------------------------------------------------
    # READ-ONLY CONTROL
    # --------------------------------------------------------

    if is_control_request(question):
        return (
            "No control command was executed. "
            "This dashboard is read-only and cannot stop, "
            "reset, move, or otherwise control the robot.",
            "READ_ONLY_CONTROL_REQUEST",
        )

    # --------------------------------------------------------
    # FLEET / MULTI-ROBOT
    # --------------------------------------------------------

    if is_fleet_question(question):
        if not fleet:
            return None

        by_id = {
            item.get("robot_id"): item
            for item in fleet
        }

        # Most attention: prioritize explicit strongest conditions.
        if (
            "most attention" in q
            or "needs the most attention" in q
        ):
            def attention_key(item):
                due_items = (
                    item.get("maintenance_due_items")
                    or []
                )

                overdue = sum(
                    1
                    for x in due_items
                    if x.get("status") == "OVERDUE"
                )

                due_soon = sum(
                    1
                    for x in due_items
                    if x.get("status") == "DUE_SOON"
                )

                return (
                    overdue,
                    item.get("active_alarm_count") or 0,
                    item.get("predictive_alert_count") or 0,
                    due_soon,
                    1
                    if item.get("mechanical_status")
                    == "ATTENTION"
                    else 0,
                )

            robot = max(
                fleet,
                key=attention_key,
            )

            due_items = (
                robot.get("maintenance_due_items")
                or []
            )

            overdue_count = sum(
                1
                for item in due_items
                if item.get("status") == "OVERDUE"
            )

            return (
                f"{_robot_label(robot)} needs the most attention "
                f"in the current synthetic fleet. It has "
                f"{robot.get('active_alarm_count', 0)} active alarm(s), "
                f"{overdue_count} overdue maintenance item(s), "
                f"{robot.get('predictive_alert_count', 0)} predictive "
                f"alert(s), and mechanical status "
                f"{robot.get('mechanical_status')}.",
                "FLEET_COMPARISON",
            )

        # Most maintenance items due/overdue.
        if (
            "most maintenance items" in q
            or "most maintenance" in q
        ):
            counts = {
                item.get("robot_id"):
                    item.get("maintenance_due_count")
                    or 0
                for item in fleet
            }

            max_count = max(counts.values())

            winners = [
                robot_id
                for robot_id, count in counts.items()
                if count == max_count
            ]

            if len(winners) > 1:
                return (
                    f"It is a tie: {', '.join(winners)} each have "
                    f"{max_count} maintenance item(s) that are "
                    "DUE_SOON or OVERDUE.",
                    "FLEET_COMPARISON",
                )

            return (
                f"{winners[0]} has the most maintenance items "
                f"due or overdue, with {max_count}.",
                "FLEET_COMPARISON",
            )


        # Fleet overdue maintenance.
        if (
            "overdue maintenance" in q
            or (
                "maintenance" in q
                and "overdue" in q
            )
        ):
            overdue = [
                item
                for item in all_maintenance
                if item.get("status") == "OVERDUE"
            ]

            if not overdue:
                return (
                    "No robot has an OVERDUE maintenance item "
                    "in the current synthetic fleet.",
                    "FLEET_COMPARISON",
                )

            return (
                " ".join(
                    f"{item.get('robot_id')} has "
                    f"{item.get('title')} "
                    f"({item.get('maintenance_id')}) marked OVERDUE."
                    for item in overdue
                ),
                "FLEET_COMPARISON",
            )

        # OEE ranking.
        if (
            "compare all robots" in q
            and "oee" in q
        ):
            ranked = sorted(
                fleet,
                key=lambda item:
                    item.get("oee_pct")
                    if item.get("oee_pct") is not None
                    else -1,
                reverse=True,
            )

            return (
                "OEE from highest to lowest: "
                + "; ".join(
                    f"{_robot_label(item)} "
                    f"{_fmt(item.get('oee_pct'))}%"
                    for item in ranked
                )
                + ".",
                "FLEET_COMPARISON",
            )

        if (
            "lowest oee" in q
            or "least oee" in q
        ):
            robot = min(
                fleet,
                key=lambda item:
                    item.get("oee_pct")
                    if item.get("oee_pct") is not None
                    else float("inf"),
            )

            return (
                f"{_robot_label(robot)} has the lowest OEE "
                f"at {_fmt(robot.get('oee_pct'))}%.",
                "FLEET_COMPARISON",
            )

        if "highest oee" in q:
            robot = max(
                fleet,
                key=lambda item:
                    item.get("oee_pct")
                    if item.get("oee_pct") is not None
                    else -1,
            )

            return (
                f"{_robot_label(robot)} has the highest OEE "
                f"at {_fmt(robot.get('oee_pct'))}%.",
                "FLEET_COMPARISON",
            )

        # Current Axis 4 load.
        if (
            "axis 4" in q
            and "historical" not in q
            and (
                "highest" in q
                or "which robot" in q
            )
        ):
            robot = max(
                fleet,
                key=lambda item:
                    item.get("axis_4_current_load_pct")
                    if item.get("axis_4_current_load_pct")
                    is not None
                    else -1,
            )

            return (
                f"{_robot_label(robot)} has the highest current "
                f"Axis 4 load at "
                f"{_fmt(robot.get('axis_4_current_load_pct'))}%.",
                "FLEET_COMPARISON",
            )

        # Current power.
        if (
            "current power" in q
            or "power consumption" in q
        ):
            robot = max(
                fleet,
                key=lambda item:
                    item.get("current_power_kw")
                    if item.get("current_power_kw")
                    is not None
                    else -1,
            )

            return (
                f"{_robot_label(robot)} has the highest current "
                f"power consumption at "
                f"{_fmt(robot.get('current_power_kw'))} kW.",
                "FLEET_COMPARISON",
            )

        # Current accumulated energy reading.
        if (
            "total energy reading" in q
            or (
                "highest total energy" in q
                and "historical" not in q
            )
        ):
            robot = max(
                fleet,
                key=lambda item:
                    item.get("total_energy_kwh")
                    if item.get("total_energy_kwh")
                    is not None
                    else -1,
            )

            return (
                f"{_robot_label(robot)} has the highest total "
                f"energy reading at "
                f"{_fmt(robot.get('total_energy_kwh'))} kWh.",
                "FLEET_COMPARISON",
            )

        # Current active alarms.
        if (
            "active alarm" in q
            and (
                "fleet" in q
                or "which robot" in q
                or "which robots" in q
            )
        ):
            active = [
                item
                for item in fleet
                if (
                    item.get("active_alarm_count")
                    or 0
                ) > 0
            ]

            if not active:
                return (
                    "No robot currently has an active alarm.",
                    "FLEET_COMPARISON",
                )

            return (
                "Currently active alarms: "
                + "; ".join(
                    f"{_robot_label(item)} — "
                    f"{', '.join(item.get('active_alarm_ids') or [])}"
                    for item in active
                )
                + ".",
                "FLEET_COMPARISON",
            )

        # Most historical faulted minutes.
        if (
            "historical faulted minutes" in q
            or "most historical faulted" in q
        ):
            robot = max(
                fleet_history,
                key=lambda item:
                    item.get("faulted_minutes")
                    or 0,
            )

            return (
                f"{robot.get('robot_id')} had the most historical "
                f"faulted minutes with "
                f"{robot.get('faulted_minutes', 0)} minutes.",
                "FLEET_COMPARISON",
            )


        # Current FAULTED state.
        if "faulted" in q:
            faulted = [
                item
                for item in fleet
                if item.get("robot_state")
                == "FAULTED"
            ]

            if not faulted:
                states = "; ".join(
                    f"{item.get('robot_id')} is "
                    f"{item.get('robot_state')}"
                    for item in fleet
                )

                return (
                    "No. None of the robots are currently FAULTED. "
                    f"{states}.",
                    "FLEET_COMPARISON",
                )

            return (
                "Currently FAULTED: "
                + ", ".join(
                    _robot_label(item)
                    for item in faulted
                )
                + ".",
                "FLEET_COMPARISON",
            )

        # Named-robot comparison.
        ids = robot_ids_in_question(question)

        if (
            len(ids) >= 2
            and "compare" in q
        ):
            rows = [
                by_id[robot_id]
                for robot_id in ids
                if robot_id in by_id
            ]

            include_state = "state" in q
            include_oee = "oee" in q
            include_alarms = "alarm" in q
            include_maintenance = "maintenance" in q
            include_axis4 = "axis 4" in q
            include_power = "power" in q

            if not any(
                (
                    include_state,
                    include_oee,
                    include_alarms,
                    include_maintenance,
                    include_axis4,
                    include_power,
                )
            ):
                include_state = True
                include_oee = True
                include_alarms = True

            parts = []

            for item in rows:
                fields = []

                if include_state:
                    fields.append(
                        f"state {item.get('robot_state')}"
                    )

                if include_oee:
                    fields.append(
                        f"OEE {_fmt(item.get('oee_pct'))}%"
                    )

                if include_alarms:
                    alarms_text = (
                        ", ".join(
                            item.get("active_alarm_ids")
                            or []
                        )
                        or "none"
                    )
                    fields.append(
                        f"active alarms {alarms_text}"
                    )

                if include_maintenance:
                    due = (
                        item.get("maintenance_due_items")
                        or []
                    )
                    due_text = (
                        ", ".join(
                            f"{x.get('maintenance_id')} "
                            f"{x.get('status')}"
                            for x in due
                        )
                        if due
                        else "none"
                    )
                    fields.append(
                        f"maintenance due {due_text}"
                    )

                if include_axis4:
                    fields.append(
                        "Axis 4 load "
                        f"{_fmt(item.get('axis_4_current_load_pct'))}%"
                    )

                if include_power:
                    fields.append(
                        "current power "
                        f"{_fmt(item.get('current_power_kw'))} kW"
                    )

                parts.append(
                    f"{_robot_label(item)}: "
                    + ", ".join(fields)
                    + "."
                )

            return (
                " ".join(parts),
                "FLEET_COMPARISON",
            )

        # Most predictive alerts.
        if "most predictive alerts" in q:
            max_count = max(
                item.get("predictive_alert_count")
                or 0
                for item in fleet
            )

            winners = [
                item
                for item in fleet
                if (
                    item.get("predictive_alert_count")
                    or 0
                ) == max_count
            ]

            if len(winners) > 1:
                return (
                    "It is a tie: "
                    + ", ".join(
                        _robot_label(item)
                        for item in winners
                    )
                    + f" each have {max_count} predictive alert(s).",
                    "FLEET_COMPARISON",
                )

            robot = winners[0]

            return (
                f"{_robot_label(robot)} has the most predictive "
                f"alerts with {max_count}.",
                "FLEET_COMPARISON",
            )

        # Highest historical axis load.
        if (
            "historical axis load" in q
            or (
                "highest axis load" in q
                and "historical" in q
            )
        ):
            robot = max(
                fleet_history,
                key=lambda item:
                    (
                        item.get(
                            "highest_historical_axis_load",
                            {},
                        ).get("load_pct")
                        if item.get(
                            "highest_historical_axis_load",
                            {},
                        ).get("load_pct") is not None
                        else -1
                    ),
            )

            axis = robot.get(
                "highest_historical_axis_load",
                {},
            )

            return (
                f"{robot.get('robot_id')} has the highest "
                f"historical axis load at "
                f"{_fmt(axis.get('load_pct'))}% on Axis "
                f"{axis.get('axis')}.",
                "FLEET_COMPARISON",
            )

        # Historical energy used.
        if (
            "used the most energy" in q
            or (
                "historical" in q
                and "energy" in q
            )
        ):
            robot = max(
                fleet_history,
                key=lambda item:
                    item.get("energy_used_kwh")
                    if item.get("energy_used_kwh")
                    is not None
                    else -1,
            )

            return (
                f"{robot.get('robot_id')} used the most energy "
                f"over the historical telemetry period at "
                f"{_fmt(robot.get('energy_used_kwh'))} kWh.",
                "FLEET_COMPARISON",
            )

        # Mechanical ATTENTION robots.
        if (
            "mechanical status attention" in q
            or (
                "mechanical" in q
                and "attention" in q
            )
        ):
            attention = [
                item
                for item in fleet
                if item.get("mechanical_status")
                == "ATTENTION"
            ]

            if not attention:
                return (
                    "No robot currently has mechanical status ATTENTION.",
                    "FLEET_COMPARISON",
                )

            return (
                "Robots with mechanical status ATTENTION: "
                + ", ".join(
                    _robot_label(item)
                    for item in attention
                )
                + ".",
                "FLEET_COMPARISON",
            )

        # Highest cycle count.
        if "highest cycle count" in q:
            robot = max(
                fleet,
                key=lambda item:
                    item.get("cycle_count_total")
                    if item.get("cycle_count_total")
                    is not None
                    else -1,
            )

            return (
                f"{_robot_label(robot)} has the highest current "
                f"cycle count at "
                f"{robot.get('cycle_count_total')} cycles.",
                "FLEET_COMPARISON",
            )

    # --------------------------------------------------------
    # SELECTED / NAMED ROBOT
    # --------------------------------------------------------

    robot_id = (
        current.get("robot_id")
        or evidence.get("selected_robot_id")
    )

    robot_name = (
        current.get("display_name")
        or current.get("robot_name")
    )

    robot_label = (
        f"{robot_id} ({robot_name})"
        if robot_name
        else robot_id
    )

    # Current state.
    if (
        "current state" in q
        or "current status" in q
        or "robot status" in q
    ):
        return (
            f"The current state of {robot_label} is "
            f"{current.get('robot_state')}.",
            "SELECTED_ROBOT_IDENTITY_AND_STATUS",
        )

    # Active alarm.
    if "active alarm" in q:
        active_ids = (
            current.get("active_alarm_ids")
            or []
        )

        if not active_ids:
            return (
                f"{robot_id} currently has no active alarms.",
                "SELECTED_ROBOT_ALARMS",
            )

        active_details = [
            alarm
            for alarm in alarms
            if alarm.get("alarm_id")
            in active_ids
        ]

        if active_details:
            alarm = active_details[0]

            return (
                f"The current active alarm on {robot_id} is "
                f"{alarm.get('alarm_id')}, a "
                f"{alarm.get('severity')} severity "
                f"{alarm.get('category')} alarm: "
                f"{alarm.get('message')}",
                "SELECTED_ROBOT_ALARMS",
            )

        return (
            f"{robot_id} currently has active alarm(s): "
            f"{', '.join(active_ids)}.",
            "SELECTED_ROBOT_ALARMS",
        )

    # Historical axis load.
    if (
        "historical axis load" in q
        or (
            "highest historical" in q
            and "axis" in q
        )
    ):
        axis = historical.get(
            "highest_historical_axis_load",
            {},
        )

        return (
            f"The highest historical axis load for {robot_id} "
            f"was {_fmt(axis.get('load_pct'))}% on Axis "
            f"{axis.get('axis')}.",
            "SELECTED_ROBOT_AXIS_AND_SERVO",
        )

    # Current Axis 4 load.
    if (
        "axis 4" in q
        and (
            "current" in q
            or "load" in q
        )
    ):
        axis4 = next(
            (
                axis
                for axis in current.get(
                    "axis_status",
                    [],
                )
                if axis.get("axis") == 4
            ),
            {},
        )

        return (
            f"The current Axis 4 load on {robot_id} is "
            f"{_fmt(axis4.get('load_pct'))}%.",
            "SELECTED_ROBOT_AXIS_AND_SERVO",
        )

    # OEE.
    if "oee" in q:
        return (
            f"The current OEE of {robot_id} is "
            f"{_fmt(current.get('oee_pct'))}%. "
            "It is an AIonOS-derived synthetic dashboard KPI; "
            "the supplied data dictionary does not define its "
            "calculation formula.",
            "SELECTED_ROBOT_OEE",
        )

    # Predictive maintenance recommendation before generic maintenance.
    if (
        "predictive maintenance" in q
        or "recommendation" in q
        or "recommended action" in q
    ):
        predictive = [
            item
            for item in insights
            if item.get("category")
            == "PREDICTIVE_MAINTENANCE"
        ]

        if not predictive:
            return (
                f"No predictive-maintenance insight is recorded "
                f"for {robot_id}.",
                "SELECTED_ROBOT_PREDICTIVE_MAINTENANCE",
            )

        item = predictive[0]

        return (
            f"{item.get('title')}. "
            f"{item.get('explanation')} "
            f"Recommended action: "
            f"{item.get('recommended_action')}",
            "SELECTED_ROBOT_PREDICTIVE_MAINTENANCE",
        )

    # Due / overdue maintenance.
    if (
        "maintenance" in q
        or "overdue" in q
    ):
        if "overdue" in q:
            due = [
                item
                for item in maintenance
                if item.get("status") == "OVERDUE"
            ]
        else:
            due = [
                item
                for item in maintenance
                if item.get("status") in {
                    "OVERDUE",
                    "DUE_SOON",
                }
            ]

        if not due:
            return (
                f"{robot_id} has no maintenance item matching "
                "that due-status request.",
                "SELECTED_ROBOT_PREDICTIVE_MAINTENANCE",
            )

        parts = []

        for item in due:
            remaining = item.get("remaining_hours")
            remaining_text = (
                f", remaining hours {_fmt(remaining)}"
                if remaining is not None
                else ""
            )

            parts.append(
                f"{item.get('maintenance_id')}: "
                f"{item.get('title')} is "
                f"{item.get('status')}{remaining_text}. "
                f"Recommended action: "
                f"{item.get('recommended_action')}"
            )

        return (
            " ".join(parts),
            "SELECTED_ROBOT_PREDICTIVE_MAINTENANCE",
        )

    # Cycle performance.
    if (
        "cycle performance" in q
        or "cycle performance concern" in q
        or (
            "axis 4 event" in q
            and "cycle" in q
        )
    ):
        cycle_insights = [
            item
            for item in insights
            if item.get("category")
            == "CYCLE_PERFORMANCE"
        ]

        if not cycle_insights:
            return (
                f"No CYCLE_PERFORMANCE insight is recorded "
                f"for {robot_id}.",
                "SELECTED_ROBOT_CYCLE_PERFORMANCE",
            )

        item = cycle_insights[0]

        return (
            f"{item.get('title')}. "
            f"{item.get('explanation')} "
            f"Recommended action: "
            f"{item.get('recommended_action')}",
            "SELECTED_ROBOT_CYCLE_PERFORMANCE",
        )

    # Energy optimization insight before generic power/energy.
    if (
        "energy optimization" in q
        or (
            "energy" in q
            and "insight" in q
        )
    ):
        energy_insights = [
            item
            for item in insights
            if item.get("category")
            == "ENERGY_OPTIMIZATION"
        ]

        if not energy_insights:
            return (
                f"No ENERGY_OPTIMIZATION insight is recorded "
                f"for {robot_id}.",
                "SELECTED_ROBOT_ENERGY_OPTIMIZATION",
            )

        item = energy_insights[0]

        return (
            f"{item.get('title')}. "
            f"{item.get('explanation')} "
            f"Recommended action: "
            f"{item.get('recommended_action')}",
            "SELECTED_ROBOT_ENERGY_OPTIMIZATION",
        )

    # Current power.
    if (
        "current power" in q
        or "power consumption" in q
    ):
        return (
            f"The current power consumption of {robot_id} is "
            f"{_fmt(current.get('current_power_kw'))} kW.",
            "SELECTED_ROBOT_POWER_AND_ENERGY",
        )

    return None


# ============================================================
# QUESTION-AWARE EVIDENCE SELECTION
# ============================================================

def select_evidence_for_question(
    question: str,
    evidence: dict,
):
    q = question.lower().strip()

    current = evidence.get(
        "current_state",
        {},
    )

    historical = evidence.get(
        "selected_robot_historical_analytics",
        {},
    )

    alarms = evidence.get(
        "selected_robot_alarm_history",
        [],
    )

    maintenance = evidence.get(
        "selected_robot_maintenance",
        [],
    )

    insights = evidence.get(
        "selected_robot_insights",
        [],
    )

    data_dictionary = evidence.get(
        "data_dictionary",
        {},
    )

    selected = {
        "evidence_type":
            evidence.get("evidence_type"),

        "system_mode":
            evidence.get("system_mode"),

        "selected_robot_id":
            evidence.get("selected_robot_id"),

        "important_interpretation_rules":
            evidence.get(
                "important_interpretation_rules",
                [],
            ),
    }

    # READ-ONLY CONTROL
    if is_control_request(question):
        selected["query_scope"] = (
            "READ_ONLY_CONTROL_REQUEST"
        )

        selected["control_capability"] = {
            "can_execute_commands": False,
            "read_only": True,
            "executed_command": None,
        }

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "robot_state":
                current.get("robot_state"),
        }

        return selected

    # FLEET
    if is_fleet_question(question):
        selected["query_scope"] = (
            "FLEET_COMPARISON"
        )

        selected["fleet_summary"] = (
            evidence.get(
                "fleet_summary",
                [],
            )
        )

        if any(
            term in q
            for term in (
                "historical",
                "history",
                "maximum",
                "highest load",
                "energy used",
                "used the most energy",
                "faulted minutes",
            )
        ):
            selected[
                "fleet_historical_analytics"
            ] = evidence.get(
                "fleet_historical_analytics",
                {},
            )

        if any(
            term in q
            for term in (
                "maintenance",
                "attention",
                "predictive",
                "inspection",
            )
        ):
            selected["all_maintenance"] = (
                evidence.get(
                    "all_maintenance",
                    [],
                )
            )

            selected["all_insights"] = (
                evidence.get(
                    "all_insights",
                    [],
                )
            )

        if "alarm" in q:
            selected["all_alarms"] = (
                evidence.get(
                    "all_alarms",
                    [],
                )
            )

        return selected

    # IDENTITY / CURRENT STATUS
    if (
        "robot id" in q
        or "robot_id" in q
        or "robot name" in q
        or "current robot state" in q
        or "current state" in q
        or "robot status" in q
        or "current status" in q
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_IDENTITY_AND_STATUS"
        )

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "robot_name":
                current.get("robot_name"),
            "display_name":
                current.get("display_name"),
            "role": current.get("role"),
            "robot_state":
                current.get("robot_state"),
            "working_status":
                current.get("working_status"),
            "process_status":
                current.get("process_status"),
            "mechanical_status":
                current.get("mechanical_status"),
        }

        return selected

    # ACTIVE ALARMS
    if "alarm" in q:
        active_ids = set(
            current.get(
                "active_alarm_ids",
                [],
            )
            or []
        )

        selected["query_scope"] = (
            "SELECTED_ROBOT_ALARMS"
        )

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "active_alarm_count":
                current.get(
                    "active_alarm_count"
                ),
            "active_alarm_ids":
                list(active_ids),
        }

        selected["alarm_history"] = alarms

        selected["active_alarm_details"] = [
            alarm
            for alarm in alarms
            if alarm.get("alarm_id")
            in active_ids
        ]

        return selected

    # CYCLE PERFORMANCE — before generic KPI performance.
    if (
        "cycle performance" in q
        or "cycle performance concern" in q
        or (
            "axis 4 event" in q
            and "cycle" in q
        )
        or "cycle degradation" in q
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_CYCLE_PERFORMANCE"
        )

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "cycle_count_total":
                current.get("cycle_count_total"),
            "current_cycle_time_s":
                current.get(
                    "current_cycle_time_s"
                ),
            "target_cycle_time_s":
                current.get(
                    "target_cycle_time_s"
                ),
            "running_rate":
                current.get("running_rate"),
        }

        selected["alarm_history"] = [
            alarm
            for alarm in alarms
            if alarm.get("category")
            == "PROCESS"
        ]

        selected["derived_insights"] = [
            item
            for item in insights
            if item.get("category")
            == "CYCLE_PERFORMANCE"
        ]

        return selected

    # ENERGY OPTIMIZATION — before generic energy.
    if (
        "energy optimization" in q
        or (
            "energy" in q
            and "insight" in q
        )
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_ENERGY_OPTIMIZATION"
        )

        selected["derived_insights"] = [
            item
            for item in insights
            if item.get("category")
            == "ENERGY_OPTIMIZATION"
        ]

        return selected

    # OEE / KPI
    if (
        "oee" in q
        or "availability" in q
        or (
            "performance" in q
            and "cycle" not in q
        )
        or "quality" in q
        or "derived kpi" in q
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_OEE"
        )

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "availability_pct":
                current.get("availability_pct"),
            "performance_pct":
                current.get("performance_pct"),
            "quality_pct":
                current.get("quality_pct"),
            "oee_pct":
                current.get("oee_pct"),
        }

        source_entry = find_dictionary_field(
            data_dictionary,
            "derived_kpis.*",
        )

        selected["oee_field_interpretation"] = {
            "source_entry":
                source_entry
                or {
                    "field": "derived_kpis.*",
                    "source_mapping":
                        "AIonOS-derived",
                    "unit": "%",
                    "purpose":
                        "OEE/availability/performance/"
                        "quality dashboard KPIs",
                },

            "native_fanuc_field_claim": False,

            "calculation_formula_available":
                False,

            "instruction": (
                "Do not invent formulas. "
                "The synthetic data dictionary "
                "does not define the formula."
            ),
        }

        return selected

    # MAINTENANCE
    if (
        "maintenance" in q
        or "overdue" in q
        or "inspection" in q
        or "predictive" in q
        or "recommended action" in q
        or "recommendation" in q
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_PREDICTIVE_MAINTENANCE"
        )

        selected["maintenance"] = maintenance

        selected["derived_insights"] = [
            item
            for item in insights
            if item.get("category") in {
                "PREDICTIVE_MAINTENANCE",
                "ANOMALY",
            }
        ]

        return selected

    # AXIS / SERVO
    if (
        "axis" in q
        or "servo" in q
        or "load" in q
        or "anomaly" in q
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_AXIS_AND_SERVO"
        )

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "axis_status":
                current.get(
                    "axis_status",
                    [],
                ),
        }

        selected["historical_analytics"] = {
            "highest_historical_axis_load":
                historical.get(
                    "highest_historical_axis_load",
                    {},
                )
        }

        selected["alarm_history"] = [
            alarm
            for alarm in alarms
            if alarm.get("category") in {
                "SERVO",
                "MECHANICAL",
            }
        ]

        selected["derived_insights"] = [
            item
            for item in insights
            if item.get("category")
            == "ANOMALY"
        ]

        return selected

    # POWER / ENERGY
    if (
        "power" in q
        or "energy" in q
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_POWER_AND_ENERGY"
        )

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "current_power_kw":
                current.get("current_power_kw"),
            "total_energy_kwh":
                current.get("total_energy_kwh"),
        }

        selected["historical_analytics"] = {
            "full_history":
                historical.get(
                    "full_history",
                    {},
                )
        }

        return selected

    # ATTENTION SUMMARY
    if (
        "needs attention" in q
        or "need attention" in q
        or "attention right now" in q
        or "what should i check" in q
    ):
        due_items = [
            item
            for item in maintenance
            if item.get("status") in {
                "OVERDUE",
                "DUE_SOON",
            }
        ]

        selected["query_scope"] = (
            "SELECTED_ROBOT_ATTENTION_SUMMARY"
        )

        selected["current_state"] = {
            "robot_id": current.get("robot_id"),
            "robot_state":
                current.get("robot_state"),
            "mechanical_status":
                current.get(
                    "mechanical_status"
                ),
            "active_alarm_ids":
                current.get(
                    "active_alarm_ids",
                    [],
                ),
        }

        selected["maintenance"] = due_items
        selected["derived_insights"] = insights

        return selected

    # HISTORICAL
    if (
        "historical" in q
        or "history" in q
        or "maximum" in q
    ):
        selected["query_scope"] = (
            "SELECTED_ROBOT_HISTORICAL_ANALYTICS"
        )

        selected["historical_analytics"] = historical

        return selected

    # SAFE DEFAULT
    selected["query_scope"] = (
        "SELECTED_ROBOT_CURRENT_STATE"
    )

    selected["current_state"] = current

    return selected


# ============================================================
# ASK MY ROBOT ENDPOINT
# ============================================================

@router.post("/ask-my-robot")
def ask_my_robot(request: AskRobotRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    try:
        fleet, robots = load_fleet()

        default_robot_id = (
            normalize_robot_id(
                request.selected_robot_id
            )
            or normalize_robot_id(
                (
                    request.live_snapshot
                    or {}
                ).get("robot_id")
            )
            or robots[0].get("robot_id")
        )

        explicit_ids = robot_ids_in_question(
            question
        )

        target_robot_id = (
            explicit_ids[0]
            if (
                len(explicit_ids) == 1
                and not is_fleet_question(
                    question
                )
            )
            else default_robot_id
        )

        live_snapshot = request.live_snapshot

        if (
            live_snapshot
            and live_snapshot.get("robot_id")
            != target_robot_id
        ):
            live_snapshot = None

        full_evidence = build_evidence(
            live_snapshot=live_snapshot,
            selected_robot_id=target_robot_id,
        )

        evidence = select_evidence_for_question(
            question,
            full_evidence,
        )

        deterministic = (
            deterministic_answer_for_question(
                question,
                full_evidence,
            )
        )

        if deterministic is not None:
            answer, deterministic_scope = deterministic
            evidence["query_scope"] = deterministic_scope
            answer_source = "DETERMINISTIC_ANALYTICS"
        else:
            answer = ask_ollama(
                question,
                evidence,
            )
            answer_source = (
                "OLLAMA_GROUNDED_EXPLANATION"
            )

        has_alarm_evidence = any(
            key in evidence
            for key in (
                "alarm_history",
                "active_alarm_details",
                "all_alarms",
            )
        )

        return {
            "question": question,
            "answer": answer,
            "model": OLLAMA_MODEL,
            "mode": "SIMULATOR",
            "read_only": True,
            "answer_source": answer_source,
            "selected_robot_id":
                target_robot_id,
            "query_scope":
                evidence.get(
                    "query_scope"
                ),

            "evidence_scope": {
                "selected_robot_snapshot":
                    "current_state"
                    in evidence,

                "fleet_comparison":
                    "fleet_summary"
                    in evidence,

                "historical_telemetry":
                    (
                        "historical_analytics"
                        in evidence
                        or
                        "fleet_historical_analytics"
                        in evidence
                    ),

                "alarms":
                    has_alarm_evidence,

                "maintenance":
                    (
                        "maintenance"
                        in evidence
                        or
                        "all_maintenance"
                        in evidence
                    ),

                "derived_insights":
                    (
                        "derived_insights"
                        in evidence
                        or
                        "all_insights"
                        in evidence
                    ),

                "data_dictionary":
                    (
                        "oee_field_interpretation"
                        in evidence
                    ),
            },
        }

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Ask My Robot failed: "
                f"{exc}"
            ),
        ) from exc
