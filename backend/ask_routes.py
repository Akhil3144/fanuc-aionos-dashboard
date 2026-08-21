from __future__ import annotations

import json
import re
from datetime import timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ollama_client import ask_ollama, OLLAMA_MODEL


# ============================================================
# PATHS — OPEN HOUSE SYNTHETIC SIMULATOR DATA
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "public" / "data_openhouse"

TELEMETRY_FILE = DATA_DIR / "telemetry_history.json"
HISTORY_DIR = DATA_DIR / "history"
FLEET_LATEST_FILE = DATA_DIR / "robot_current.json"
ALARMS_FILE = DATA_DIR / "alarms.json"
MAINTENANCE_FILE = DATA_DIR / "maintenance.json"
INSIGHTS_FILE = DATA_DIR / "insights.json"
REGISTRY_FILE = DATA_DIR / "robot_registry.json"
DATA_DICTIONARY_FILE = DATA_DIR / "data_dictionary.json"
DETERMINISTIC_ANSWER_CACHE = {}


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
    robot_id: str | None = None
    scope: str | None = None

    # Real Open House identity/configuration supplied by the frontend.
    # Operational telemetry remains sourced from the simulator files.
    selected_registry_id: str | None = None
    robot_registry: list[dict] = Field(default_factory=list)


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
    fleet = load_json(FLEET_LATEST_FILE) or []
    robots = fleet if isinstance(fleet, list) else fleet.get("robots", [])

    if not isinstance(robots, list) or not robots:
        raise RuntimeError(
            "robot_current.json contains no robots"
        )

    return {"robots": robots, "source_mode": "SIMULATOR"}, robots


def robot_by_id(robots, robot_id):
    return next(
        (
            robot
            for robot in robots
            if robot.get("robot_id") == robot_id
        ),
        None,
    )


class RobotResolutionError(RuntimeError):
    pass


def get_openhouse_robot_evidence(robot_id):
    normalized = normalize_robot_id(robot_id)
    if not normalized or not normalized.startswith("OH26-"):
        raise RobotResolutionError(f"{robot_id} is not an Open House robot ID")
    registry = load_json(REGISTRY_FILE) or []
    current = load_json(FLEET_LATEST_FILE) or []
    sources = {
        "production": load_json(DATA_DIR / "production.json") or [],
        "axis_servo": load_json(DATA_DIR / "axis_servo.json") or [],
        "alarms": load_json(ALARMS_FILE) or [], "maintenance": load_json(MAINTENANCE_FILE) or [],
        "power": load_json(DATA_DIR / "power.json") or [], "insights": load_json(INSIGHTS_FILE) or [],
    }
    resolved = next((item for item in current if item.get("robot_id") == normalized), None)
    registry_item = next((item for item in registry if item.get("id") == normalized), None)
    if not resolved or not registry_item:
        raise RobotResolutionError(f"Open House data was not found for {normalized}")
    result = {"robot_id": normalized, "registry": registry_item, "current": resolved, "data_source": "OPENHOUSE"}
    for name, rows in sources.items():
        matches = [item for item in rows if item.get("robot_id") == normalized]
        result[name] = matches if name in {"alarms", "maintenance", "insights"} else (matches[0] if matches else None)
    result["history_summary"] = build_robot_historical_evidence(normalized)
    if result["robot_id"] != normalized:
        raise RobotResolutionError(f"Robot resolution mismatch: requested {normalized}, resolved {result['robot_id']}")
    return result


def normalize_robot_id(value):
    if not value:
        return None

    match = re.search(r"\bOH26[-_ ]?R0?([0-9]{1,3})\b", str(value).upper())

    if not match:
        return None

    return f"OH26-R{int(match.group(1)):03d}"


def robot_ids_in_question(question):
    ids = []

    for match in re.finditer(r"\bOH26[-_ ]?R0?([0-9]{1,3})\b", question.upper()):
        robot_id = f"OH26-R{int(match.group(1)):03d}"

        if robot_id not in ids:
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


@lru_cache(maxsize=16)
def build_robot_historical_evidence(robot_id):
    points = load_json(HISTORY_DIR / f"{robot_id}.json") or []
    if not points:
        raise RuntimeError(f"No simulator history found for {robot_id}")

    def stats(field, higher_is_better=None):
        values = [float(point[field]) for point in points if point.get(field) is not None]
        if not values:
            return {"min": None, "max": None, "average": None, "latest": None, "trend": "STABLE"}
        window = max(2, min(12, len(values) // 2))
        delta = sum(values[-window:]) / window - sum(values[:window]) / window
        threshold = max((max(values) - min(values)) * 0.08, 0.05)
        if abs(delta) <= threshold or higher_is_better is None:
            trend = "STABLE"
        else:
            improving = delta > 0 if higher_is_better else delta < 0
            trend = "IMPROVING" if improving else "DEGRADING"
        return {"min": round(min(values), 2), "max": round(max(values), 2), "average": round(sum(values) / len(values), 2), "latest": round(values[-1], 2), "trend": trend}

    axis_stats = {f"J{axis}": stats(f"axis{axis}_load_pct", False) for axis in range(1, 7)}
    highest_axis = max(axis_stats.items(), key=lambda item: item[1]["max"] or -1)
    alarms = [item for item in (load_json(ALARMS_FILE) or []) if item.get("robot_id") == robot_id]
    maintenance = [item for item in (load_json(MAINTENANCE_FILE) or []) if item.get("robot_id") == robot_id]
    return {
        "robot_id": robot_id,
        "source_mode": "SIMULATOR",
        "full_history": {
            "records": len(points), "start_time": points[0].get("timestamp"), "end_time": points[-1].get("timestamp"),
            "cycle_time_s": stats("cycle_time_s", False), "oee_pct": stats("oee_pct", True),
            "cycle_deviation_pct": stats("cycle_deviation_pct", False),
            "availability_pct": stats("availability_pct", True), "performance_pct": stats("performance_pct", True),
            "quality_pct": stats("quality_pct", True), "power_kw": stats("power_kw", False),
            "servo_error_count": stats("servo_error_count"),
            "faulted_samples": sum(point.get("state") == "FAULTED" for point in points),
            "state_counts": {
                state: sum(point.get("state") == state for point in points)
                for state in ("RUNNING", "READY", "IDLE", "FAULTED")
            },
            "alarm_sample_count": sum((point.get("active_alarm_count") or 0) > 0 for point in points),
        },
        "axis_load_trends": axis_stats,
        "highest_historical_axis_load": {"axis": highest_axis[0], "load_pct": highest_axis[1]["max"], "measurement_type": "historical maximum"},
        "alarm_windows": alarms,
        "maintenance_status": maintenance,
    }

    # Retained below only as documentation of the previous V3 DuckDB query.
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


@lru_cache(maxsize=1)
def build_fleet_historical_evidence():
    _, robots = load_fleet()
    rows = []
    for robot in robots:
        evidence = build_robot_historical_evidence(robot["robot_id"])
        full = evidence["full_history"]
        interval_hours = (1 if full["records"] == 120 else 5) / 60
        rows.append({
            "robot_id": robot["robot_id"],
            "records": full["records"],
            "average_cycle_time_s": full["cycle_time_s"]["average"],
            "faulted_minutes": full["faulted_samples"] * (1 if full["records"] == 120 else 5),
            "energy_used_kwh": round(full["power_kw"]["average"] * full["records"] * interval_hours, 2),
            "peak_power_kw": full["power_kw"]["max"],
            "highest_historical_axis_load": evidence["highest_historical_axis_load"],
        })
    return {
        "source_mode": "SIMULATOR",
        "robots": rows,
    }

    # Retained below only as documentation of the previous V3 DuckDB query.
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
                "CYCLE_DEGRADATION",
                "AXIS_LOAD_TREND",
                "POWER_ANOMALY",
                "MAINTENANCE_DUE",
                "ALARM_PATTERN",
                "HEALTH_ATTENTION",
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
    robot_registry=None,
    selected_registry_id=None,
):
    fleet, robots = load_fleet()

    alarms = load_json(ALARMS_FILE) or []
    maintenance = load_json(MAINTENANCE_FILE) or []
    insights = load_json(INSIGHTS_FILE) or []
    data_dictionary = (
        load_json(DATA_DICTIONARY_FILE)
        or {}
    )

    raw_requested_id = selected_robot_id or (live_snapshot or {}).get("robot_id")
    requested_id = normalize_robot_id(raw_requested_id)

    if raw_requested_id and requested_id is None:
        raise RobotResolutionError(f"Robot {raw_requested_id} is not available in the Open House data source")

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
        raise RobotResolutionError(
            f"Robot {requested_id} was not found "
            "in the Open House dataset."
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

        "registry_source": "OPEN HOUSE 2026",
        "robot_registry": robot_registry or [],
        "selected_registry_id": selected_registry_id,
        "selected_robot_registry": next(
            (
                item for item in (robot_registry or [])
                if item.get("id") == selected_registry_id
            ),
            None,
        ),

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
        "set robot speed",
        "change the robot speed",
        "reduce speed",
        "increase speed",
        "change override",
        "set override",
        "write register",
        "modify io",
        "modify i/o",
        "change io",
        "change i/o",
        "disable a safety interlock",
        "disable safety interlock",
    )

    return any(term in q for term in control_terms)


def is_explanation_request(question):
    return classify_complex_intent(question) is not None


def classify_complex_intent(question):
    """Resolve complex reasoning prompts before topic-based evidence routing."""
    if is_control_request(question):
        return None

    q = re.sub(r"\s+", " ", question.lower()).strip()
    rules = (
        ("AI_FLEET_MAINTENANCE_PRIORITY", ("maintenance resources are limited", "inspections be prioritized")),
        ("AI_FLEET_ROBOT_RANKING", ("most concerning robots", "evidence behind your ranking")),
        ("AI_FLEET_RISK_PRIORITY", ("operational risks across the fleet", "management attention first", "overall fleet risk summary")),
        ("AI_FLEET_PATTERN_SUMMARY", ("patterns across the fleet", "performance, maintenance, alarm, and energy patterns")),
        ("AI_FLEET_EXECUTIVE_SUMMARY", ("executive summary of the overall fleet", "executive summary")),
        ("AI_MAINTENANCE_ENGINEER_REVIEW", ("maintenance engineer reviewing", "next maintenance window")),
        ("AI_HISTORICAL_COMPARISON", ("compare the robot's current condition", "historical behavior", "current condition with its recent")),
        ("AI_TREND_ASSESSMENT", ("improving, stable, or degrading", "condition is improving")),
        ("AI_OPERATIONAL_RISK", ("three biggest operational concerns", "biggest operational concerns")),
        ("AI_INSPECTION_PRIORITY", ("inspect first", "inspection priority")),
        ("AI_RECENT_CHANGE_ANALYSIS", ("what changed recently", "which changes deserve", "important changes in recent telemetry")),
        ("AI_ALARM_CONTEXT", ("latest alarm", "around the latest alarm", "alarm in the context")),
        ("AI_ATTENTION_EXPLANATION", ("why this robot currently requires attention", "why this robot requires attention", "why this robot needs attention")),
        ("AI_MAINTENANCE_RISK", ("most important maintenance risk",)),
        ("AI_MULTI_SIGNAL_ANALYSIS", ("relationship between", "analyze its power consumption", "analyze the relationship")),
        ("AI_ENGINEERING_ASSESSMENT", ("engineering assessment", "in one assessment", "executive summary of this robot")),
        ("AI_CONDITION_SUMMARY", ("complete condition summary", "condition summary")),
    )
    for intent, phrases in rules:
        if any(phrase in q for phrase in phrases):
            return intent
    return None


def is_fleet_question(question, request_scope=None):
    q = question.lower()
    ids = robot_ids_in_question(question)

    if str(request_scope or "").upper() == "ROBOT":
        return len(ids) >= 2 or any(term in q for term in (
            "which robot", "which robots", "all robots", "fleet", "across the fleet", "compare robots",
        ))

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
        "how many robots",
        "currently running",
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
    request_scope=None,
):
    """
    Exact-answer layer for factual V3 simulator questions.

    Deterministic analytics owns ranking, comparisons and direct
    lookups. Ollama is reserved for open-ended grounded explanation.
    """
    q = question.lower().strip()

    registry = evidence.get("robot_registry", []) or []
    selected_registry = evidence.get("selected_robot_registry") or {}

    # Real registry identity/configuration answers. These never infer telemetry.
    if registry:
        if (("how many robots" in q or "robot count" in q) and ("registry" in q or "open house" in q)):
            return (f"The Open House 2026 registry contains {len(registry)} robots.", "FLEET_REGISTRY")

        if "which applications" in q or "applications are represented" in q or "application count" in q:
            applications = sorted({item.get("application") for item in registry if item.get("application")})
            return (f"The registry contains {len(applications)} specified applications: {', '.join(applications)}. Robots with blank application cells are not included in that count.", "FLEET_REGISTRY")

        if "featured" in q and selected_registry and ("is it" in q or str(selected_registry.get("id", "")).lower() in q):
            return (
                f"{selected_registry.get('id')} is "
                f"{'featured' if selected_registry.get('featured') else 'not featured'} "
                "in the real Open House 2026 Excel registry.",
                "SELECTED_ROBOT_REGISTRY",
            )

        if "featured" in q:
            featured = [item for item in registry if item.get("featured")]
            labels = "; ".join(f"{item.get('id')} — {item.get('model')} ({item.get('application')})" for item in featured)
            return (f"The featured robots are {labels}.", "FLEET_REGISTRY")

        exact_application_matches = [
            item for item in registry
            if item.get("application")
            and str(item.get("application")).lower() in q
        ]
        if exact_application_matches and ("which robot" in q or "which robots" in q or "used for" in q):
            labels = "; ".join(f"{item.get('id')} — {item.get('model')} ({item.get('application')})" for item in exact_application_matches)
            return (labels + ".", "FLEET_REGISTRY")

        application_terms = ("pallet", "picking", "ai error proofing", "assembly", "welding", "paint", "packaging", "handling")
        matched_term = next((term for term in application_terms if term in q), None)
        if matched_term and ("which robot" in q or "which robots" in q or "used for" in q):
            matches = [item for item in registry if matched_term in str(item.get("application") or "").lower()]
            if matches:
                labels = "; ".join(f"{item.get('id')} — {item.get('model')} ({item.get('application')})" for item in matches)
                return (labels + ".", "FLEET_REGISTRY")
            return (f"No robot has a specified application matching '{matched_term}' in the Open House 2026 registry.", "FLEET_REGISTRY")

        registry_target = selected_registry
        for item in registry:
            identifiers = (str(item.get("id") or ""), str(item.get("model") or ""), str(item.get("serialNo") or ""))
            if any(identifier and identifier.lower() in q for identifier in identifiers[:2]):
                registry_target = item
                break

        if registry_target and any(term in q for term in ("model", "application", "ip", "identity", "what robot")):
            ip_address = registry_target.get("ipAddress") or "not available in the workbook"
            application = registry_target.get("application") or "not specified in the workbook"
            return (f"{registry_target.get('id')} is serial {registry_target.get('serialNo')}, model {registry_target.get('model')}, application {application}, IP address {ip_address}, and featured is {str(bool(registry_target.get('featured'))).lower()}.", "SELECTED_ROBOT_REGISTRY")

        if selected_registry and "telemetry" in q and ("available" in q or "simulator" in q):
            return (
                "Available operational evidence includes simulator state, OEE, cycle data, power and energy, "
                "alarms, maintenance, and axis/servo measurements. These values are SIMULATOR data, "
                "not live FANUC/ZDT telemetry.",
                "SELECTED_ROBOT_SIMULATOR_EVIDENCE",
            )

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

    if any(term in q for term in ("definitely fail", "definitely break", "will fail tomorrow", "break next")):
        return (
            "The available simulator evidence cannot determine a definite future failure. "
            "No unsupported prediction will be fabricated.",
            "SAFE_GROUNDED_REFUSAL",
        )

    if "axis value" in q and "not in the evidence" in q:
        return (
            "The available evidence is insufficient to provide that axis value, so no value will be fabricated.",
            "SAFE_GROUNDED_REFUSAL",
        )

    if ("sensor value" in q or "measurement" in q) and any(term in q for term in ("not present", "not available", "not in the evidence")):
        return ("The available evidence is insufficient to provide that measurement, so no value will be fabricated.", "SAFE_GROUNDED_REFUSAL")

    if "prove" in q and any(term in q for term in ("caused", "cause", "root cause")):
        return ("The evidence shows correlation only and does not prove causation or a root cause.", "SAFE_GROUNDED_REFUSAL")

    if "live fanuc" in q or "live from fanuc" in q or "directly live from fanuc" in q or "directly from zdt" in q or "zdt right now" in q or "zdt live" in q:
        return (
            "No. Operational telemetry is SIMULATOR data and is not coming directly from live FANUC/ZDT systems right now. "
            "Robot identity and application metadata come from the real Open House 2026 Excel registry.",
            "DATA_PROVENANCE",
        )

    if "control robot safety" in q or "control safety" in q or "dashboard control the robot" in q or "safety controller" in q:
        return (
            "No. This dashboard is READ ONLY and cannot control robots or robot safety functions.",
            "READ_ONLY_CONTROL_REQUEST",
        )

    # --------------------------------------------------------
    # FLEET / MULTI-ROBOT
    # --------------------------------------------------------

    if is_fleet_question(question, request_scope):
        if not fleet:
            return None

        by_id = {
            item.get("robot_id"): item
            for item in fleet
        }

        if "running" in q and ("how many" in q or "count" in q):
            running = [item for item in fleet if item.get("robot_state") == "RUNNING"]
            return (
                f"In the current SIMULATOR snapshot, {len(running)} robots are RUNNING: "
                + ", ".join(item.get("robot_id") for item in running)
                + ".",
                "FLEET_COMPARISON",
            )

        if ("idle" in q or "ready" in q) and ("how many" in q or "count" in q):
            matching = [item for item in fleet if item.get("robot_state") in {"IDLE", "READY"}]
            return (
                f"In the current SIMULATOR snapshot, {len(matching)} robots are IDLE or READY: "
                + ", ".join(f"{item.get('robot_id')} ({item.get('robot_state')})" for item in matching)
                + ".",
                "FLEET_COMPARISON",
            )

        if "healthy" in q and ("how many" in q or "count" in q):
            healthy = [item for item in fleet if item.get("mechanical_status") == "NORMAL"]
            return (f"In the current SIMULATOR snapshot, {len(healthy)} robots have NORMAL mechanical health.", "FLEET_COMPARISON")

        if "attention" in q and ("how many" in q or "count" in q):
            attention = [item for item in fleet if item.get("mechanical_status") in {"ATTENTION", "CRITICAL"}]
            return (f"In the current SIMULATOR snapshot, {len(attention)} robots have ATTENTION or CRITICAL mechanical health.", "FLEET_COMPARISON")

        if "fleet" in q and ("condition summary" in q or "condition" in q or "summary" in q):
            running = sum(1 for item in fleet if item.get("robot_state") == "RUNNING")
            alarms = sum(item.get("active_alarm_count") or 0 for item in fleet)
            attention = sum(1 for item in fleet if item.get("mechanical_status") == "ATTENTION")
            maintenance_due = sum(item.get("maintenance_due_count") or 0 for item in fleet)
            return (
                f"SIMULATOR fleet summary: {len(fleet)} telemetry profiles, {running} RUNNING, "
                f"{alarms} active alarm(s), {attention} with mechanical ATTENTION, and "
                f"{maintenance_due} maintenance item(s) due or overdue.",
                "FLEET_COMPARISON",
            )

        if ("highest current axis load" in q or "highest axis load" in q) and "axis 4" not in q:
            robot = max(fleet, key=lambda item: (item.get("highest_current_axis") or {}).get("load_pct") or -1)
            axis = robot.get("highest_current_axis") or {}
            return (
                f"In the SIMULATOR snapshot, {_robot_label(robot)} has the highest current axis load "
                f"at {_fmt(axis.get('load_pct'))}% on Axis {axis.get('axis')}.",
                "FLEET_COMPARISON",
            )

        if "which robot" in q and "maintenance due" in q:
            due = [item for item in fleet if (item.get("maintenance_due_count") or 0) > 0]
            if not due:
                return ("No simulator robot has maintenance due or overdue.", "FLEET_COMPARISON")
            return (
                "SIMULATOR robots with maintenance due or overdue: "
                + "; ".join(f"{_robot_label(item)} — {item.get('maintenance_due_count')} item(s)" for item in due)
                + ".",
                "FLEET_COMPARISON",
            )

        # Most attention: prioritize explicit strongest conditions.
        if (
            "most attention" in q
            or "needs the most attention" in q
            or "need the most attention" in q
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
                f"in the current modelled fleet. It has "
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
                    "in the current modelled fleet.",
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
    history_full = historical.get("full_history", {}) or {}
    cycle_history = history_full.get("cycle_time_s", {}) or {}
    power_history = history_full.get("power_kw", {}) or {}
    oee_history = history_full.get("oee_pct", {}) or {}

    if "cycle time" in q and any(term in q for term in ("average", "minimum", " min ", "maximum", " max ")):
        return (
            f"For {robot_id}, historical cycle time minimum is {_fmt(cycle_history.get('min'))} seconds, maximum is {_fmt(cycle_history.get('max'))} seconds, and average is {_fmt(cycle_history.get('average'))} seconds.",
            "SELECTED_ROBOT_HISTORICAL_ANALYTICS",
        )
    if "cycle trend" in q:
        return (f"The calculated cycle-time trend for {robot_id} is {cycle_history.get('trend', 'STABLE')}.", "SELECTED_ROBOT_HISTORICAL_ANALYTICS")
    if "power" in q and any(term in q for term in ("average", "maximum", " max ")):
        return (f"For {robot_id}, historical power average is {_fmt(power_history.get('average'))} kW and maximum is {_fmt(power_history.get('max'))} kW; trend is {power_history.get('trend', 'STABLE')}.", "SELECTED_ROBOT_POWER_AND_ENERGY")
    if "oee" in q and "historical average" in q:
        relation = "above" if (current.get("oee_pct") or 0) > (oee_history.get("average") or 0) else "below"
        return (f"{robot_id} current OEE is {_fmt(current.get('oee_pct'))}%, {relation} its historical average of {_fmt(oee_history.get('average'))}%.", "SELECTED_ROBOT_OEE")

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

    if ("axis" in q and "highest load" in q) or "axis needs attention first" in q:
        axes = current.get("axis_status", [])
        highest = max(axes, key=lambda item: item.get("load_pct") or -1) if axes else {}
        return (
            f"{robot_id} has its highest current measured load on Axis {highest.get('axis')} at {_fmt(highest.get('load_pct'))}%. This is a measured association, not evidence of causation.",
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

    # Recent changes and evidence-grounded inspection guidance.
    if any(term in q for term in ("what changed recently", "changed before", "happened around the latest alarm", "cycle performance changing", "inspect first", "inspected first")):
        if not insights:
            return (
                f"No derived simulator insight records a recent material change for {robot_id}.",
                "SELECTED_ROBOT_HISTORICAL_ANALYTICS",
            )
        details = "; ".join(
            f"{item.get('title')}: {item.get('evidence')} Recommendation: {item.get('recommendation') or item.get('recommended_action')}"
            for item in insights[:3]
        )
        return (
            f"SIMULATOR trend evidence for {robot_id}: {details} These are correlated observations, not proven root cause.",
            "SELECTED_ROBOT_HISTORICAL_ANALYTICS",
        )

    # OEE.
    if "oee" in q:
        return (
            f"The current OEE of {robot_id} is "
            f"{_fmt(current.get('oee_pct'))}%. "
            "It is an AIonOS-derived modelled operational KPI; "
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
            if item.get("category") in {
                "PREDICTIVE_MAINTENANCE", "MAINTENANCE_DUE",
                "CYCLE_DEGRADATION", "AXIS_LOAD_TREND",
                "POWER_ANOMALY", "ALARM_PATTERN", "HEALTH_ATTENTION",
            }
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
            f"{item.get('evidence') or item.get('explanation')} "
            f"Recommended action: "
            f"{item.get('recommendation') or item.get('recommended_action')}",
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

    # Current / target cycle time.
    if "how far" in q and "cycle time" in q and "target" in q:
        current_cycle = current.get("current_cycle_time_s")
        target_cycle = current.get("target_cycle_time_s")
        deviation = None if current_cycle is None or target_cycle in (None, 0) else round(current_cycle - target_cycle, 2)
        deviation_pct = None if deviation is None else round(deviation / target_cycle * 100, 1)
        direction = "slower" if (deviation or 0) > 0 else "faster"
        return (f"{robot_id} is cycling at {_fmt(current_cycle)} seconds versus a {_fmt(target_cycle)}-second target, {_fmt(abs(deviation) if deviation is not None else None)} seconds ({_fmt(abs(deviation_pct) if deviation_pct is not None else None)}%) {direction}.", "SELECTED_ROBOT_CYCLE_PERFORMANCE")

    if "cycle time" in q and "performance" not in q:
        return (
            f"For {robot_id}, the current cycle time is "
            f"{_fmt(current.get('current_cycle_time_s'))} seconds and the target cycle time is "
            f"{_fmt(current.get('target_cycle_time_s'))} seconds in the modelled operational evidence.",
            "SELECTED_ROBOT_CYCLE_PERFORMANCE",
        )

    if "current cycle performance" in q or "cycle performance changing" in q:
        history_cycle = (historical.get("full_history") or {}).get("cycle_time_s") or {}
        return (
            f"For {robot_id}, current cycle time is {_fmt(current.get('current_cycle_time_s'))} seconds versus a {_fmt(current.get('target_cycle_time_s'))}-second target. Historical average is {_fmt(history_cycle.get('average'))} seconds and the trend is {history_cycle.get('trend', 'STABLE')}.",
            "SELECTED_ROBOT_CYCLE_PERFORMANCE",
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
    if "power compare with history" in q or "power compared with history" in q:
        history_power = (historical.get("full_history") or {}).get("power_kw") or {}
        current_power = current.get("current_power_kw")
        average_power = history_power.get("average")
        difference_pct = None if current_power is None or average_power in (None, 0) else round((current_power - average_power) / average_power * 100, 1)
        return (
            f"{robot_id} currently uses {_fmt(current_power)} kW versus a {_fmt(average_power)} kW historical average ({_fmt(abs(difference_pct) if difference_pct is not None else None)}% {'higher' if (difference_pct or 0) > 0 else 'lower'}); historical maximum is {_fmt(history_power.get('max'))} kW and trend is {history_power.get('trend', 'STABLE')}.",
            "SELECTED_ROBOT_POWER_AND_ENERGY",
        )

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

def select_complex_intent_evidence(intent, evidence):
    """Build a compact evidence package tailored to one reasoning intent."""
    current = evidence.get("current_state", {})
    historical = evidence.get("selected_robot_historical_analytics", {})
    base = {
        "evidence_type": evidence.get("evidence_type"),
        "system_mode": evidence.get("system_mode"),
        "source_mode": "SIMULATOR",
        "selected_robot_id": evidence.get("selected_robot_id"),
        "query_scope": intent,
        "resolved_intent": intent,
        "important_interpretation_rules": evidence.get("important_interpretation_rules", []),
    }
    if intent.startswith("AI_FLEET_"):
        base["fleet_summary"] = evidence.get("fleet_summary", [])
        base["fleet_historical_analytics"] = evidence.get("fleet_historical_analytics", {})
        if intent in {"AI_FLEET_MAINTENANCE_PRIORITY", "AI_FLEET_RISK_PRIORITY", "AI_FLEET_ROBOT_RANKING", "AI_FLEET_PATTERN_SUMMARY"}:
            base["all_maintenance"] = evidence.get("all_maintenance", [])
            base["all_alarms"] = evidence.get("all_alarms", [])
            base["all_insights"] = evidence.get("all_insights", [])
        return base

    base["current_state"] = current
    base["historical_analytics"] = historical
    if intent in {"AI_ALARM_CONTEXT", "AI_MULTI_SIGNAL_ANALYSIS", "AI_OPERATIONAL_RISK", "AI_ENGINEERING_ASSESSMENT", "AI_ATTENTION_EXPLANATION", "AI_MAINTENANCE_ENGINEER_REVIEW", "AI_MAINTENANCE_RISK", "AI_CONDITION_SUMMARY", "AI_RECENT_CHANGE_ANALYSIS"}:
        base["alarm_history"] = evidence.get("selected_robot_alarm_history", [])
    if intent in {"AI_INSPECTION_PRIORITY", "AI_MULTI_SIGNAL_ANALYSIS", "AI_OPERATIONAL_RISK", "AI_ENGINEERING_ASSESSMENT", "AI_ATTENTION_EXPLANATION", "AI_MAINTENANCE_ENGINEER_REVIEW", "AI_MAINTENANCE_RISK", "AI_CONDITION_SUMMARY", "AI_RECENT_CHANGE_ANALYSIS"}:
        base["maintenance"] = evidence.get("selected_robot_maintenance", [])
        base["derived_insights"] = evidence.get("selected_robot_insights", [])
    return base


def _metric(history, key):
    return ((history.get("full_history") or {}).get(key) or {})


def _latest_alarm(full_evidence):
    alarms = full_evidence.get("selected_robot_alarm_history", [])
    return max(alarms, key=lambda item: item.get("started_at") or "", default=None)


def _priority_maintenance(full_evidence):
    rank = {"OVERDUE": 0, "DUE_SOON": 1}
    items = full_evidence.get("selected_robot_maintenance", [])
    return min(items, key=lambda item: (rank.get(item.get("status"), 2), item.get("remaining_hours", 10**9)), default=None)


def _highest_axis(current):
    return max(current.get("axis_status", []), key=lambda item: item.get("load_pct") or -1, default={})


def _fleet_ranking(full_evidence):
    def score(robot):
        overdue = sum(item.get("status") == "OVERDUE" for item in robot.get("maintenance_due_items", []))
        due = robot.get("maintenance_due_count", 0)
        alarms = robot.get("active_alarm_count", 0)
        attention = robot.get("mechanical_status") == "ATTENTION"
        load = (robot.get("highest_current_axis") or {}).get("load_pct") or 0
        oee = robot.get("oee_pct") or 100
        return overdue * 100 + alarms * 30 + due * 15 + attention * 10 + max(0, 92 - oee) + load / 20
    return sorted(full_evidence.get("fleet_summary", []), key=score, reverse=True)


def fallback_for_complex_intent(intent, full_evidence):
    """Useful, evidence-only answers that remain distinct when Ollama is offline."""
    current = full_evidence.get("current_state", {})
    history = full_evidence.get("selected_robot_historical_analytics", {})
    robot_id = current.get("robot_id") or full_evidence.get("selected_robot_id")
    cycle, oee, power = (_metric(history, key) for key in ("cycle_time_s", "oee_pct", "power_kw"))
    axis = _highest_axis(current)
    alarm = _latest_alarm(full_evidence)
    maintenance = _priority_maintenance(full_evidence)
    insights = full_evidence.get("selected_robot_insights", [])
    trends = [cycle.get("trend"), oee.get("trend"), power.get("trend")]

    if intent == "AI_CONDITION_SUMMARY":
        return (f"{robot_id} is {current.get('robot_state')} with {current.get('oee_pct')}% OEE and {current.get('current_cycle_time_s')} s cycle time versus {current.get('target_cycle_time_s')} s target. "
                f"Its highest current load is Axis {axis.get('axis')} at {axis.get('load_pct')}%, with {current.get('active_alarm_count')} active alarm(s); maintenance is {maintenance.get('status') if maintenance else 'not due'}. Simulator telemetry only.")
    if intent == "AI_RECENT_CHANGE_ANALYSIS":
        changed = [f"cycle time is {cycle.get('trend')} (latest {cycle.get('latest')} s vs {cycle.get('average')} s average)",
                   f"OEE is {oee.get('trend')} (latest {oee.get('latest')}% vs {oee.get('average')}% average)",
                   f"power is {power.get('trend')} (latest {power.get('latest')} kW vs {power.get('average')} kW average)"]
        axis_trends = history.get("axis_load_trends", {})
        degrading_axes = [name for name, stats in axis_trends.items() if stats.get("trend") == "DEGRADING"]
        return "Recent changes are: " + "; ".join(changed) + f". Axes with degrading load trends: {', '.join(degrading_axes) or 'none'}. Attention should follow the recorded alarm and maintenance status, without inferring causation."
    if intent == "AI_INSPECTION_PRIORITY":
        if maintenance:
            return f"Inspect {maintenance.get('component')} first because maintenance is {maintenance.get('status')} with {maintenance.get('remaining_hours')} hours remaining. {maintenance.get('recommended_action')} The highest current measured load is Axis {axis.get('axis')} at {axis.get('load_pct')}%."
        return f"Inspect the evidence behind the highest current load, Axis {axis.get('axis')} at {axis.get('load_pct')}%, first; no overdue or due-soon maintenance item is supplied."
    if intent == "AI_ALARM_CONTEXT":
        if not alarm:
            return f"No alarm event is available for {robot_id}; an event-window assessment cannot be made."
        return (f"Latest alarm event: {alarm.get('alarm_id')} ({alarm.get('severity')}) started {alarm.get('started_at')}: {alarm.get('message')}. "
                f"Around the available history window, cycle is {cycle.get('trend')} at {cycle.get('latest')} s versus {cycle.get('average')} s average, power is {power.get('trend')}, and Axis {axis.get('axis')} is currently highest at {axis.get('load_pct')}%. These are associated observations, not a confirmed cause.")
    if intent == "AI_MULTI_SIGNAL_ANALYSIS":
        servo = sum(item.get("error_count") or 0 for item in current.get("axis_status", []))
        return (f"Multi-signal analysis for {robot_id}: cycle {cycle.get('trend')} ({cycle.get('latest')} vs {cycle.get('average')} s), OEE {oee.get('trend')} ({oee.get('latest')} vs {oee.get('average')}%), "
                f"power {power.get('trend')} ({power.get('latest')} vs {power.get('average')} kW), highest current load Axis {axis.get('axis')} at {axis.get('load_pct')}%, and {servo} current servo error count(s). The signals coincide but do not establish causation.")
    if intent == "AI_OPERATIONAL_RISK":
        concerns = []
        if maintenance: concerns.append(f"{maintenance.get('status')} maintenance — {maintenance.get('title')} ({maintenance.get('remaining_hours')} hours remaining)")
        if alarm: concerns.append(f"Active {alarm.get('severity')} alarm — {alarm.get('message')}")
        concerns.append(f"Performance trend — cycle is {cycle.get('trend')} at {cycle.get('latest')} s versus {cycle.get('average')} s average")
        return "\n".join(f"{i}. {text}" for i, text in enumerate(concerns[:3], 1))
    if intent == "AI_ENGINEERING_ASSESSMENT":
        action = maintenance.get("recommended_action") if maintenance else "No scheduled maintenance action is supplied."
        return (f"Engineering assessment for {robot_id}: production is {current.get('robot_state')} at {current.get('current_cycle_time_s')} s cycle and {current.get('oee_pct')}% OEE. "
                f"Health is {current.get('mechanical_status')}; Axis {axis.get('axis')} is highest at {axis.get('load_pct')}%; alarms: {current.get('active_alarm_count')}; power: {current.get('current_power_kw')} kW. {action}")
    if intent == "AI_MAINTENANCE_ENGINEER_REVIEW":
        alarm_text = alarm.get("message") if alarm else "no recorded alarm"
        maintenance_text = (f"{maintenance.get('title')} is {maintenance.get('status')} with {maintenance.get('remaining_hours')} hours remaining" if maintenance else "no scheduled item is due")
        return (f"Next maintenance window investigation:\n1. Verify {maintenance_text}.\n"
                f"2. Inspect Axis {axis.get('axis')} and its {axis.get('load_pct')}% current load against the historical axis trend.\n"
                f"3. Review the event record for {alarm_text} and the {sum(item.get('error_count') or 0 for item in current.get('axis_status', []))} current servo error count(s). Do not treat coincident signals as confirmed cause.")
    if intent == "AI_HISTORICAL_COMPARISON":
        return (f"Current cycle is {current.get('current_cycle_time_s')} s versus historical average {cycle.get('average')} s (range {cycle.get('min')}–{cycle.get('max')}); "
                f"current power is {current.get('current_power_kw')} kW versus {power.get('average')} kW average (range {power.get('min')}–{power.get('max')}); current OEE is {current.get('oee_pct')}% versus {oee.get('average')}% average (range {oee.get('min')}–{oee.get('max')}). Trends are cycle {cycle.get('trend')}, power {power.get('trend')}, OEE {oee.get('trend')}.")
    if intent == "AI_TREND_ASSESSMENT":
        degrading = sum(value == "DEGRADING" for value in trends)
        improving = sum(value == "IMPROVING" for value in trends)
        verdict = "DEGRADING" if degrading > improving else "IMPROVING" if improving > degrading else "STABLE"
        return f"{verdict} — cycle time is {cycle.get('trend')}, OEE is {oee.get('trend')}, and power is {power.get('trend')}. Latest versus average values are {cycle.get('latest')} vs {cycle.get('average')} s, {oee.get('latest')} vs {oee.get('average')}%, and {power.get('latest')} vs {power.get('average')} kW, respectively."
    if intent == "AI_ATTENTION_EXPLANATION":
        return f"{robot_id} requires attention because it has {current.get('active_alarm_count')} active alarm(s), mechanical status {current.get('mechanical_status')}, and {maintenance.get('status') if maintenance else 'no due'} maintenance. The highest current load is Axis {axis.get('axis')} at {axis.get('load_pct')}%."
    if intent == "AI_MAINTENANCE_RISK":
        if maintenance:
            return f"The primary maintenance risk is {maintenance.get('title')}: it is {maintenance.get('status')} with {maintenance.get('remaining_hours')} hours remaining. Supporting evidence includes {alarm.get('message') if alarm else 'no active alarm'}; {maintenance.get('recommended_action')}"
        return "No overdue or due-soon maintenance risk is present in the supplied simulator evidence."

    ranked = _fleet_ranking(full_evidence)
    if intent == "AI_FLEET_EXECUTIVE_SUMMARY":
        running = sum(item.get("robot_state") == "RUNNING" for item in ranked)
        alarms = sum(item.get("active_alarm_count", 0) for item in ranked)
        due = sum(item.get("maintenance_due_count", 0) for item in ranked)
        return f"Fleet executive summary: {running} of {len(ranked)} robots are RUNNING; {alarms} active alarms and {due} overdue/due-soon maintenance items are recorded. The lowest OEE is {min((r for r in ranked if r.get('oee_pct') is not None), key=lambda r:r['oee_pct'])['robot_id']}. All operational values are simulator data."
    if intent == "AI_FLEET_ROBOT_RANKING":
        return "Most concerning robots, ranked by supplied alarm, maintenance, status, OEE, and load evidence:\n" + "\n".join(f"{i}. {r['robot_id']} — alarms {r.get('active_alarm_count',0)}, maintenance items {r.get('maintenance_due_count',0)}, OEE {r.get('oee_pct')}%, highest load {(r.get('highest_current_axis') or {}).get('load_pct')}%." for i, r in enumerate(ranked[:5], 1))
    if intent == "AI_FLEET_RISK_PRIORITY":
        top = ranked[:3]
        return "Management risk priorities:\n" + "\n".join(f"{i}. {r['robot_id']}: {r.get('maintenance_due_count',0)} maintenance item(s), {r.get('active_alarm_count',0)} alarm(s), mechanical status {r.get('mechanical_status')}." for i, r in enumerate(top, 1))
    if intent == "AI_FLEET_PATTERN_SUMMARY":
        avg_oee = sum(r.get("oee_pct") or 0 for r in ranked) / len(ranked)
        avg_power = sum(r.get("current_power_kw") or 0 for r in ranked) / len(ranked)
        return f"Fleet patterns: average OEE is {avg_oee:.1f}%; {sum(r.get('maintenance_due_count',0)>0 for r in ranked)} robots have due maintenance; {sum(r.get('active_alarm_count',0)>0 for r in ranked)} have active alarms; average current power is {avg_power:.2f} kW. Highest current power is {max(ranked,key=lambda r:r.get('current_power_kw') or 0)['robot_id']}."
    if intent == "AI_FLEET_MAINTENANCE_PRIORITY":
        due = [r for r in ranked if r.get("maintenance_due_count", 0)]
        return "Inspection priority with limited resources:\n" + "\n".join(f"{i}. {r['robot_id']} — {r.get('maintenance_due_count')} due item(s), {r.get('active_alarm_count',0)} alarm(s), highest load {(r.get('highest_current_axis') or {}).get('load_pct')}%." for i, r in enumerate(due[:5], 1))
    return "The available data is insufficient to determine that."

def select_evidence_for_question(
    question: str,
    evidence: dict,
    request_scope=None,
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

    complex_intent = classify_complex_intent(question)
    if complex_intent:
        return select_complex_intent_evidence(complex_intent, evidence)

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
    if is_fleet_question(question, request_scope):
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
                "MAINTENANCE_DUE",
                "CYCLE_DEGRADATION",
                "AXIS_LOAD_TREND",
                "POWER_ANOMALY",
                "ALARM_PATTERN",
                "HEALTH_ATTENTION",
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
            if item.get("category") in {"ANOMALY", "AXIS_LOAD_TREND", "ALARM_PATTERN"}
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
        # Registry identity/configuration questions bypass telemetry and DuckDB.
        registry_evidence = {
            "robot_registry": request.robot_registry,
            "selected_registry_id": request.selected_registry_id,
            "selected_robot_registry": next(
                (
                    item for item in request.robot_registry
                    if item.get("id") == request.selected_registry_id
                ),
                None,
            ),
        }
        registry_answer = deterministic_answer_for_question(question, registry_evidence, request.scope)
        if registry_answer is not None and "REGISTRY" in registry_answer[1]:
            answer, query_scope = registry_answer
            return {
                "question": question,
                "answer": answer,
                "model": OLLAMA_MODEL,
                "mode": "SIMULATOR",
                "read_only": True,
                "answer_source": "DETERMINISTIC_ANALYTICS",
                "resolution_mode": "DETERMINISTIC",
                "selected_robot_id": request.selected_registry_id,
                "requested_robot_id": request.robot_id or request.selected_robot_id,
                "resolved_robot_id": request.selected_registry_id,
                "data_source": "OPENHOUSE_REGISTRY",
                "query_scope": query_scope,
                "intent": query_scope,
                "evidence_scope": {
                    "registry": True,
                    "selected_robot_snapshot": False,
                    "fleet_comparison": query_scope == "FLEET_REGISTRY",
                    "historical_telemetry": False,
                    "alarms": False,
                    "maintenance": False,
                    "derived_insights": False,
                    "data_dictionary": False,
                },
            }

        fleet, robots = load_fleet()

        received_robot_id = request.robot_id or request.selected_robot_id or (request.live_snapshot or {}).get("robot_id")
        if str(request.scope or "").upper() == "ROBOT" and not received_robot_id:
            raise RobotResolutionError("ROBOT scope requires an explicit robot_id")
        if received_robot_id and str(received_robot_id).upper().startswith("EXH-"):
            raise RobotResolutionError("Legacy EXH evidence is not substituted into Open House requests")

        default_robot_id = (
            normalize_robot_id(received_robot_id)
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
                and str(request.scope or "").upper() != "ROBOT"
                and not is_fleet_question(
                    question, request.scope
                )
            )
            else default_robot_id
        )
        resolved_package = get_openhouse_robot_evidence(target_robot_id)
        if received_robot_id and str(request.scope or "").upper() == "ROBOT" and normalize_robot_id(received_robot_id) != resolved_package["robot_id"]:
            raise RobotResolutionError(f"Robot resolution mismatch: requested {received_robot_id}, resolved {resolved_package['robot_id']}")

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
            robot_registry=request.robot_registry,
            selected_registry_id=request.selected_registry_id,
        )

        evidence = select_evidence_for_question(
            question,
            full_evidence,
            request.scope,
        )

        complex_intent = classify_complex_intent(question)
        if complex_intent:
            # Give the language model a compact, backend-calculated factual
            # boundary. It may improve presentation, but must not introduce
            # claims beyond this intent-specific grounded reference.
            evidence["grounded_reference_answer"] = fallback_for_complex_intent(
                complex_intent,
                full_evidence,
            )

        normalized_question = re.sub(r"\s+", " ", question.lower()).strip()
        cacheable = not is_control_request(question) and not any(term in normalized_question for term in ("definitely", "not in the evidence"))
        cache_key = (normalized_question, target_robot_id, request.selected_registry_id, str(request.scope or "").upper(), FLEET_LATEST_FILE.stat().st_mtime_ns)
        explanation_request = complex_intent is not None
        deterministic = DETERMINISTIC_ANSWER_CACHE.get(cache_key) if cacheable and not explanation_request else None
        if deterministic is None and not explanation_request:
            deterministic = deterministic_answer_for_question(question, full_evidence, request.scope)
            if deterministic is not None and cacheable:
                if len(DETERMINISTIC_ANSWER_CACHE) >= 512:
                    DETERMINISTIC_ANSWER_CACHE.clear()
                DETERMINISTIC_ANSWER_CACHE[cache_key] = deterministic

        if deterministic is not None:
            answer, deterministic_scope = deterministic
            evidence["query_scope"] = deterministic_scope
            answer_source = "DETERMINISTIC_ANALYTICS"
            resolution_mode = "DETERMINISTIC"
        else:
            q_lower = question.lower()
            try:
                answer = ask_ollama(question, evidence)
                answer_source = "OLLAMA_GROUNDED_EXPLANATION"
                resolution_mode = "AI"
            except RuntimeError:
                if complex_intent:
                    answer = fallback_for_complex_intent(complex_intent, full_evidence)
                    answer_source = "INTENT_SPECIFIC_DETERMINISTIC_FALLBACK"
                else:
                    answer = (
                        "AI explanation service is temporarily unavailable, but the dashboard evidence remains available."
                    )
                    answer_source = "AI_SERVICE_UNAVAILABLE"
                resolution_mode = "AI_FALLBACK"

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
            "resolution_mode": resolution_mode,
            "data_source": "OPENHOUSE",
            "resolved_robot_id": target_robot_id,
            "requested_robot_id": received_robot_id,
            "selected_robot_id":
                request.selected_registry_id or target_robot_id,
            "query_scope":
                evidence.get(
                    "query_scope"
                ),
            "intent": complex_intent or evidence.get("query_scope"),

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

    except RobotResolutionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
