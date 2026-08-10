from __future__ import annotations

import json
import math
import random
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
START = datetime(2026, 8, 7, 22, 0, tzinfo=IST)
MINUTES = 4320
REPLAY_SECONDS = 900
random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent
OUT = PROJECT_ROOT / "public" / "data_v3"
OUT.mkdir(parents=True, exist_ok=True)

ROBOTS = [
    {
        "robot_id": "EXH-R01",
        "robot_name": "ASSEMBLY_ROBOT_01",
        "display_name": "Assembly Robot",
        "role": "Assembly",
        "target_cycle_s": 44.0,
        "base_power_kw": 3.6,
        "program": "ASM_DEMO_101",
        "program_number": 101,
    },
    {
        "robot_id": "EXH-R02",
        "robot_name": "HANDLING_ROBOT_02",
        "display_name": "Handling Robot",
        "role": "Material Handling",
        "target_cycle_s": 46.0,
        "base_power_kw": 4.1,
        "program": "HND_DEMO_201",
        "program_number": 201,
    },
    {
        "robot_id": "EXH-R03",
        "robot_name": "PACKAGING_ROBOT_03",
        "display_name": "Packaging Robot",
        "role": "Packaging",
        "target_cycle_s": 42.0,
        "base_power_kw": 4.4,
        "program": "PKG_DEMO_301",
        "program_number": 301,
    },
]

R02_DEGRADE_START = datetime(2026, 8, 8, 14, 30, tzinfo=IST)
R02_FAULT_START = datetime(2026, 8, 8, 15, 45, tzinfo=IST)
R02_FAULT_END = datetime(2026, 8, 8, 16, 0, tzinfo=IST)
R02_DEGRADE_END = datetime(2026, 8, 8, 16, 10, tzinfo=IST)

R03_SLOW_START = datetime(2026, 8, 9, 10, 0, tzinfo=IST)
R03_SLOW_END = datetime(2026, 8, 9, 12, 0, tzinfo=IST)


def dump_json(name, obj):
    (OUT / name).write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_jsonl(name, rows):
    with (OUT / name).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def shift_for_hour(hour):
    if 6 <= hour < 14:
        return "A"
    if 14 <= hour < 22:
        return "B"
    return "C"


def state_for(robot_id, ts, minute_index):
    if robot_id == "EXH-R02" and R02_FAULT_START <= ts < R02_FAULT_END:
        return "FAULTED"

    phase = minute_index % 20

    if robot_id == "EXH-R01":
        return "RUNNING" if phase < 15 else ("IDLE" if phase < 18 else "READY")

    if robot_id == "EXH-R02":
        return "RUNNING" if phase < 13 else ("IDLE" if phase < 17 else "READY")

    return "RUNNING" if phase < 12 else ("IDLE" if phase < 16 else "READY")


def axis_load(robot_id, axis, ts, minute_index):
    base_by_axis = {
        1: 18,
        2: 22,
        3: 24,
        4: 28,
        5: 16,
        6: 14,
    }

    base = base_by_axis[axis]
    wobble = 4.0 * math.sin((minute_index + axis * 7) / 23.0)
    noise = random.uniform(-2.2, 2.2)

    if robot_id == "EXH-R01":
        extra = 3 if axis == 2 else 0

    elif robot_id == "EXH-R02":
        extra = 5 if axis == 4 else 1

        if axis == 4 and R02_DEGRADE_START <= ts <= R02_DEGRADE_END:
            total = (R02_DEGRADE_END - R02_DEGRADE_START).total_seconds()
            progress = (ts - R02_DEGRADE_START).total_seconds() / total
            spike = 44 + 42 * math.sin(min(1.0, progress) * math.pi)
            return round(max(0, min(86.5, spike + noise)), 1)

    else:
        extra = 4 if axis in (3, 5) else 0

    return round(
        max(3.0, min(78.0, base + extra + wobble + noise)),
        1,
    )


def actual_cycle_time(robot_id, ts, target, running, minute_index):
    if not running:
        return None

    value = (
        target
        + 0.8 * math.sin(minute_index / 17.0)
        + random.uniform(-0.8, 0.8)
    )

    if robot_id == "EXH-R02" and R02_DEGRADE_START <= ts <= R02_DEGRADE_END:
        total = (R02_DEGRADE_END - R02_DEGRADE_START).total_seconds()
        progress = (ts - R02_DEGRADE_START).total_seconds() / total
        value += 2.0 + 8.5 * math.sin(progress * math.pi)

    if robot_id == "EXH-R03" and R03_SLOW_START <= ts <= R03_SLOW_END:
        value += 7.0 + 2.5 * math.sin(minute_index / 8.0)

    return round(value, 2)


def instantaneous_power(robot_id, state, ts, base_power, minute_index):
    if state == "RUNNING":
        value = (
            base_power
            + 0.5 * math.sin(minute_index / 13.0)
            + random.uniform(-0.25, 0.25)
        )
    elif state == "IDLE":
        value = 1.55 + random.uniform(-0.12, 0.12)
    elif state == "READY":
        value = 0.95 + random.uniform(-0.08, 0.08)
    else:
        value = 0.65 + random.uniform(-0.05, 0.05)

    if (
        robot_id == "EXH-R03"
        and R03_SLOW_START <= ts <= R03_SLOW_END
        and state == "RUNNING"
    ):
        value += 1.45

    return round(max(0.2, value), 3)


def kpis(robot_id):
    if robot_id == "EXH-R01":
        return {
            "shift_availability_pct": 98.7,
            "shift_performance_pct": 97.3,
            "shift_quality_pct": 99.7,
            "shift_oee_pct": 95.7,
        }

    if robot_id == "EXH-R02":
        return {
            "shift_availability_pct": 96.4,
            "shift_performance_pct": 93.8,
            "shift_quality_pct": 99.4,
            "shift_oee_pct": 89.9,
        }

    return {
        "shift_availability_pct": 97.9,
        "shift_performance_pct": 90.8,
        "shift_quality_pct": 99.1,
        "shift_oee_pct": 88.1,
    }


def active_alarm_ids(robot_id, ts):
    if (
        robot_id == "EXH-R02"
        and ts >= datetime(2026, 8, 10, 18, 0, tzinfo=IST)
    ):
        return ["R02-ALM-204"]

    return []


def build_snapshot(robot, ts, minute_index, cumulative):
    robot_id = robot["robot_id"]
    state = state_for(robot_id, ts, minute_index)
    running = state == "RUNNING"

    actual_cycle = actual_cycle_time(
        robot_id,
        ts,
        robot["target_cycle_s"],
        running,
        minute_index,
    )

    cycles_this_minute = 0

    if running:
        cycles_this_minute = 1

        if robot_id == "EXH-R01" and minute_index % 4 == 0:
            cycles_this_minute += 1
        elif robot_id == "EXH-R02" and minute_index % 5 == 0:
            cycles_this_minute += 1
        elif robot_id == "EXH-R03" and minute_index % 6 == 0:
            cycles_this_minute += 1

    cumulative["cycles"] += cycles_this_minute

    reject_mod = {
        "EXH-R01": 700,
        "EXH-R02": 480,
        "EXH-R03": 350,
    }[robot_id]

    rejected = (
        1
        if cycles_this_minute and minute_index % reject_mod == 0
        else 0
    )

    cumulative["rejects"] += rejected
    cumulative["good"] += max(0, cycles_this_minute - rejected)

    if state == "RUNNING":
        cumulative["running"] += 60
    elif state == "IDLE":
        cumulative["idle"] += 60
    elif state == "READY":
        cumulative["ready"] += 60
    elif state == "FAULTED":
        cumulative["faulted"] += 60

    power_kw = instantaneous_power(
        robot_id,
        state,
        ts,
        robot["base_power_kw"],
        minute_index,
    )

    cumulative["kwh_total"] += power_kw / 60.0

    if state == "RUNNING":
        cumulative["kwh_run"] += power_kw / 60.0
    elif state == "IDLE":
        cumulative["kwh_idle"] += power_kw / 60.0
    elif state == "READY":
        cumulative["kwh_ready"] += power_kw / 60.0
    else:
        cumulative["kwh_fault"] += power_kw / 60.0

    axes = []

    for axis in range(1, 7):
        load = axis_load(
            robot_id,
            axis,
            ts,
            minute_index,
        )

        error_count = 0

        if robot_id == "EXH-R02" and axis == 4:
            error_count = 2
        elif robot_id == "EXH-R03" and axis == 5:
            error_count = 1

        indicator = "NORMAL"

        if load >= 80:
            indicator = "ATTENTION"
        elif load >= 70:
            indicator = "WATCH"

        axes.append({
            "axis": axis,
            "axis_load_pct": load,
            "error_count": error_count,
            "odometer": round(
                55000
                + axis * 9300
                + minute_index * (5.5 + axis * 0.15),
                1,
            ),
            "servo_indicator": indicator,
        })

    active_ids = active_alarm_ids(robot_id, ts)

    total_time = max(
        1,
        cumulative["running"]
        + cumulative["idle"]
        + cumulative["ready"]
        + cumulative["faulted"],
    )

    return {
        "timestamp": ts.isoformat(),
        "robot_id": robot_id,
        "robot_name": robot["robot_name"],
        "display_name": robot["display_name"],
        "role": robot["role"],
        "shift": shift_for_hour(ts.hour),
        "source_mode": "SIMULATOR",

        "connection_health": {
            "edge_connection": "CONNECTED",
            "data_quality": "GOOD",
            "stale": False,
            "latency_ms": 18 + (minute_index + int(robot_id[-1])) % 17,
            "last_good_timestamp": ts.isoformat(),
            "reconnect_count": 0,
        },

        "live_cell": {
            "state": state,
            "busy": running,

            "di": {
                "DI_001_cell_auto_request": True,
                "DI_002_part_present": running,
                "DI_003_safety_gate_closed": True,
                "DI_004_cycle_start_permit": state != "FAULTED",
            },

            "do": {
                "DO_001_robot_busy": running,
                "DO_002_cycle_complete_pulse": bool(cycles_this_minute),
                "DO_003_fault_active": state == "FAULTED",
                "DO_004_robot_ready": state in ("READY", "RUNNING"),
            },

            "registers": {
                "R_001_cycle_count": cumulative["cycles"],
                "R_002_shift_id": {
                    "A": 1,
                    "B": 2,
                    "C": 3,
                }[shift_for_hour(ts.hour)],
                "R_003_program_number": robot["program_number"],
            },

            "position_registers": {
                "PR_001_demo_pick_pose": {
                    "x_mm": 410.0 + int(robot_id[-1]) * 5,
                    "y_mm": -125.0,
                    "z_mm": 285.0,
                    "w_deg": 179.5,
                    "p_deg": 1.2,
                    "r_deg": 89.8,
                    "frame": "USER_FRAME_1",
                    "tool": "TOOL_1",
                }
            },

            "process_values": {
                "program": robot["program"],
                "line": "EXHIBITION_CELL",
                "override_pct": 100 if running else 0,
                "mode": "AUTO",
                "current_step": "PROCESS" if running else None,
            },
        },

        "production": {
            "cycles_completed_this_minute": cycles_this_minute,
            "cycle_count_total": cumulative["cycles"],
            "good_count_total": cumulative["good"],
            "reject_count_total": cumulative["rejects"],
            "target_cycle_time_s": robot["target_cycle_s"],
            "actual_cycle_time_s": actual_cycle,
            "running_time_s": cumulative["running"],
            "idle_time_s": cumulative["idle"],
            "ready_time_s": cumulative["ready"],
            "faulted_time_s": cumulative["faulted"],
            "running_rate": round(
                cumulative["running"] / total_time,
                4,
            ),
            "ready_rate": round(
                cumulative["ready"] / total_time,
                4,
            ),
        },

        "derived_kpis": kpis(robot_id),

        "robot_status": {
            "working_status":
                "WORKING"
                if state != "FAULTED"
                else "INTERRUPTED",

            "process_status":
                "NORMAL"
                if state != "FAULTED"
                else "INTERRUPTED",

            "mechanical_status":
                "NORMAL"
                if robot_id == "EXH-R01"
                else "ATTENTION",
        },

        "alarms": {
            "active_alarm_ids": active_ids,
            "active_alarm_count": len(active_ids),
        },

        "axis_servo": axes,

        "power_data": {
            "instantaneous_kw": power_kw,
            "regeneration_kw": 0.0,
            "kwh_total": round(
                cumulative["kwh_total"],
                3,
            ),
            "kwh_run": round(
                cumulative["kwh_run"],
                3,
            ),
            "kwh_idle": round(
                cumulative["kwh_idle"],
                3,
            ),
            "kwh_ready": round(
                cumulative["kwh_ready"],
                3,
            ),
            "kwh_fault": round(
                cumulative["kwh_fault"],
                3,
            ),
            "kwh_regen": 0.0,
        },
    }


def override_latest(snapshot, robot_id):
    result = deepcopy(snapshot)

    if robot_id == "EXH-R01":
        state = "RUNNING"
        axis4 = 29.4
        power = 3.82

    elif robot_id == "EXH-R02":
        state = "RUNNING"
        axis4 = 58.2
        power = 4.54

    else:
        state = "READY"
        axis4 = 31.7
        power = 1.02

    result["live_cell"]["state"] = state
    result["live_cell"]["busy"] = state == "RUNNING"
    result["live_cell"]["do"]["DO_001_robot_busy"] = state == "RUNNING"
    result["live_cell"]["do"]["DO_003_fault_active"] = False
    result["live_cell"]["do"]["DO_004_robot_ready"] = True
    result["live_cell"]["process_values"]["override_pct"] = (
        100 if state == "RUNNING" else 0
    )
    result["live_cell"]["process_values"]["current_step"] = (
        "PROCESS"
        if state == "RUNNING"
        else None
    )

    result["robot_status"]["working_status"] = "WORKING"
    result["robot_status"]["process_status"] = "NORMAL"

    for axis in result["axis_servo"]:
        if axis["axis"] == 4:
            axis["axis_load_pct"] = axis4
            axis["servo_indicator"] = "NORMAL"

    result["power_data"]["instantaneous_kw"] = power

    return result


def build():
    counters = {
        robot["robot_id"]: {
            "cycles": 0,
            "good": 0,
            "rejects": 0,
            "running": 0,
            "idle": 0,
            "ready": 0,
            "faulted": 0,
            "kwh_total": 0.0,
            "kwh_run": 0.0,
            "kwh_idle": 0.0,
            "kwh_ready": 0.0,
            "kwh_fault": 0.0,
        }
        for robot in ROBOTS
    }

    history = []
    latest = {}

    for minute_index in range(MINUTES):
        ts = START + timedelta(minutes=minute_index)

        for robot in ROBOTS:
            snapshot = build_snapshot(
                robot,
                ts,
                minute_index,
                counters[robot["robot_id"]],
            )

            history.append(snapshot)
            latest[robot["robot_id"]] = snapshot

    for robot_id in list(latest):
        latest[robot_id] = override_latest(
            latest[robot_id],
            robot_id,
        )

    write_jsonl(
        "telemetry_history.jsonl",
        history,
    )

    dump_json(
        "robots.json",
        [
            {
                "robot_id": robot["robot_id"],
                "robot_name": robot["robot_name"],
                "display_name": robot["display_name"],
                "role": robot["role"],
                "source_mode": "SIMULATOR",
            }
            for robot in ROBOTS
        ],
    )

    dump_json(
        "latest_snapshot.json",
        latest["EXH-R01"],
    )

    dump_json(
        "latest_snapshots.json",
        {
            "robots": list(latest.values())
        },
    )

    dump_json(
        "fleet_latest_snapshot.json",
        {
            "timestamp": max(
                snapshot["timestamp"]
                for snapshot in latest.values()
            ),

            "source_mode": "SIMULATOR",

            "fleet_summary": {
                "total_robots": 3,

                "running": sum(
                    1
                    for snapshot in latest.values()
                    if snapshot["live_cell"]["state"] == "RUNNING"
                ),

                "ready": sum(
                    1
                    for snapshot in latest.values()
                    if snapshot["live_cell"]["state"] == "READY"
                ),

                "faulted": sum(
                    1
                    for snapshot in latest.values()
                    if snapshot["live_cell"]["state"] == "FAULTED"
                ),

                "robots_needing_attention": sum(
                    1
                    for snapshot in latest.values()
                    if snapshot["robot_status"]["mechanical_status"]
                    == "ATTENTION"
                ),

                "active_alarms": sum(
                    snapshot["alarms"]["active_alarm_count"]
                    for snapshot in latest.values()
                ),
            },

            "robots": list(latest.values()),
        },
    )

    alarms = [
        {
            "alarm_id": "R02-ALM-201",
            "robot_id": "EXH-R02",
            "robot_name": "HANDLING_ROBOT_02",
            "severity": "HIGH",
            "category": "SERVO",
            "status": "CLEARED",
            "message":
                "Synthetic Axis 4 servo deviation detected.",
            "start_time":
                "2026-08-08T15:40:00+05:30",
            "end_time":
                "2026-08-08T15:46:00+05:30",
        },

        {
            "alarm_id": "R02-ALM-202",
            "robot_id": "EXH-R02",
            "robot_name": "HANDLING_ROBOT_02",
            "severity": "HIGH",
            "category": "PROCESS",
            "status": "CLEARED",
            "message":
                "Synthetic process cycle interrupted after sustained Axis 4 load increase.",
            "start_time":
                "2026-08-08T15:45:00+05:30",
            "end_time":
                "2026-08-08T16:00:00+05:30",
        },

        {
            "alarm_id": "R02-ALM-204",
            "robot_id": "EXH-R02",
            "robot_name": "HANDLING_ROBOT_02",
            "severity": "LOW",
            "category": "MECHANICAL",
            "status": "ACTIVE",
            "message":
                "Synthetic Axis 4 load trend requires inspection.",
            "start_time":
                "2026-08-10T18:00:00+05:30",
            "end_time": None,
        },

        {
            "alarm_id": "R03-ALM-301",
            "robot_id": "EXH-R03",
            "robot_name": "PACKAGING_ROBOT_03",
            "severity": "MEDIUM",
            "category": "PROCESS",
            "status": "CLEARED",
            "message":
                "Synthetic cycle-time drift detected during packaging operation.",
            "start_time":
                "2026-08-09T10:20:00+05:30",
            "end_time":
                "2026-08-09T11:45:00+05:30",
        },
    ]

    dump_json(
        "alarms.json",
        alarms,
    )

    maintenance = [
        {
            "maintenance_id": "R01-MNT-101",
            "robot_id": "EXH-R01",
            "title": "Controller cabinet inspection",
            "component": "Controller Cabinet",
            "priority": "MEDIUM",
            "status": "DUE_SOON",
            "remaining_hours": 48,
            "reason":
                "Scheduled preventive inspection window is approaching.",
            "recommended_action":
                "Plan the controller cabinet inspection during the next available maintenance window.",
        },

        {
            "maintenance_id": "R02-MNT-201",
            "robot_id": "EXH-R02",
            "title": "Axis 4 mechanical and servo inspection",
            "component": "Axis 4",
            "priority": "HIGH",
            "status": "OVERDUE",
            "remaining_hours": -3,
            "reason":
                "Repeated synthetic Axis 4 abnormal-load and servo/process events are present in the evidence.",
            "recommended_action":
                "Inspect Axis 4 mechanical and servo condition before sustained production.",
        },

        {
            "maintenance_id": "R02-MNT-202",
            "robot_id": "EXH-R02",
            "title": "General mechanical inspection",
            "component": "Robot Mechanical",
            "priority": "LOW",
            "status": "OK",
            "remaining_hours": 280,
            "reason":
                "No additional scheduled mechanical maintenance is currently due.",
            "recommended_action":
                "Continue normal monitoring.",
        },

        {
            "maintenance_id": "R03-MNT-301",
            "robot_id": "EXH-R03",
            "title": "Gripper / end-effector inspection",
            "component": "End Effector",
            "priority": "MEDIUM",
            "status": "DUE_SOON",
            "remaining_hours": 14,
            "reason":
                "The preventive maintenance window is approaching while cycle performance has degraded.",
            "recommended_action":
                "Inspect the gripper/end-effector during the next planned maintenance stop.",
        },

        {
            "maintenance_id": "R03-MNT-302",
            "robot_id": "EXH-R03",
            "title": "Controller cabinet inspection",
            "component": "Controller Cabinet",
            "priority": "LOW",
            "status": "OK",
            "remaining_hours": 190,
            "reason":
                "Scheduled maintenance remains within its normal remaining-life range.",
            "recommended_action":
                "Continue normal monitoring.",
        },
    ]

    dump_json(
        "maintenance.json",
        maintenance,
    )

    insights = [
        {
            "insight_id": "R01-INS-101",
            "robot_id": "EXH-R01",
            "category": "PREDICTIVE_MAINTENANCE",
            "severity": "INFO",
            "title":
                "Controller inspection window approaching",
            "explanation":
                "The scheduled controller cabinet inspection is due within 48 operating hours.",
            "recommended_action":
                "Plan the inspection during the next available maintenance window.",
            "evidence": ["R01-MNT-101"],
        },

        {
            "insight_id": "R02-INS-201",
            "robot_id": "EXH-R02",
            "category": "ANOMALY",
            "severity": "HIGH",
            "title":
                "Axis 4 abnormal-load pattern detected",
            "explanation":
                "Axis 4 load increased above its normal operating pattern during the synthetic degradation window.",
            "recommended_action":
                "Review Axis 4 mechanical and servo condition.",
            "evidence": [
                "R02-ALM-201",
                "R02-ALM-202",
            ],
        },

        {
            "insight_id": "R02-INS-202",
            "robot_id": "EXH-R02",
            "category": "PREDICTIVE_MAINTENANCE",
            "severity": "HIGH",
            "title":
                "Axis 4 inspection recommended",
            "explanation":
                "The Axis 4 inspection is overdue and the history contains repeated abnormal-load and servo/process events.",
            "recommended_action":
                "Inspect Axis 4 mechanical and servo condition before sustained production.",
            "evidence": [
                "R02-MNT-201",
                "R02-ALM-201",
                "R02-ALM-202",
                "R02-ALM-204",
            ],
        },

        {
            "insight_id": "R02-INS-203",
            "robot_id": "EXH-R02",
            "category": "CYCLE_PERFORMANCE",
            "severity": "MEDIUM",
            "title":
                "Cycle degradation observed during Axis 4 event",
            "explanation":
                "Actual cycle time increased during the same degradation window in which Axis 4 load increased.",
            "recommended_action":
                "Review the Axis 4 event before increasing the production rate.",
            "evidence": [
                "R02-ALM-202",
            ],
        },

        {
            "insight_id": "R03-INS-301",
            "robot_id": "EXH-R03",
            "category": "CYCLE_PERFORMANCE",
            "severity": "HIGH",
            "title":
                "Packaging cycle performance loss detected",
            "explanation":
                "Actual cycle time remained above the target pattern during the synthetic packaging slowdown window.",
            "recommended_action":
                "Review packaging process timing and the stage contributing to cycle loss.",
            "evidence": [
                "R03-ALM-301",
            ],
        },

        {
            "insight_id": "R03-INS-302",
            "robot_id": "EXH-R03",
            "category": "ENERGY_OPTIMIZATION",
            "severity": "MEDIUM",
            "title":
                "Elevated energy usage during slow cycles",
            "explanation":
                "Power usage increased during the same period in which packaging cycle time was elevated.",
            "recommended_action":
                "Review idle/running power behavior together with packaging cycle efficiency.",
            "evidence": [
                "R03-ALM-301",
            ],
        },

        {
            "insight_id": "R03-INS-303",
            "robot_id": "EXH-R03",
            "category": "PREDICTIVE_MAINTENANCE",
            "severity": "MEDIUM",
            "title":
                "End-effector inspection approaching",
            "explanation":
                "The gripper/end-effector preventive maintenance window is due within 14 operating hours.",
            "recommended_action":
                "Inspect the gripper/end-effector during the next planned maintenance stop.",
            "evidence": [
                "R03-MNT-301",
            ],
        },
    ]

    dump_json(
        "derived_insights.json",
        insights,
    )

    summaries = []

    for robot in ROBOTS:
        snapshot = latest[robot["robot_id"]]

        summaries.append({
            "robot_id": robot["robot_id"],
            "robot_name": robot["robot_name"],
            "display_name": robot["display_name"],
            "shift": snapshot["shift"],
            "cycles_completed":
                snapshot["production"]["cycle_count_total"],
            "good_count":
                snapshot["production"]["good_count_total"],
            "reject_count":
                snapshot["production"]["reject_count_total"],
            "target_cycle_time_s":
                snapshot["production"]["target_cycle_time_s"],
            "shift_oee_pct":
                snapshot["derived_kpis"]["shift_oee_pct"],
            "availability_pct":
                snapshot["derived_kpis"]["shift_availability_pct"],
            "performance_pct":
                snapshot["derived_kpis"]["shift_performance_pct"],
            "quality_pct":
                snapshot["derived_kpis"]["shift_quality_pct"],
        })

    dump_json(
        "production_shift_summary.json",
        summaries,
    )

    data_dictionary = [
        {
            "field": "robot_id",
            "domain": "Fleet",
            "source_mapping":
                "ZDT robot identifier / AIonOS normalized key",
            "unit": None,
            "purpose":
                "Select and compare robots in a multi-robot dashboard",
        },

        {
            "field": "live_cell.state",
            "domain": "Operations",
            "source_mapping":
                "OPC UA / AIonOS normalized",
            "unit": None,
            "purpose":
                "Current selected-robot operating state",
        },

        {
            "field": "production.*",
            "domain": "Production & Cycle",
            "source_mapping":
                "ZDT Production / AIonOS normalized",
            "unit": "mixed",
            "purpose":
                "Cycle counts, cycle time and operating-time analytics",
        },

        {
            "field": "derived_kpis.*",
            "domain": "Production & Cycle",
            "source_mapping": "AIonOS-derived",
            "unit": "%",
            "purpose":
                "OEE/availability/performance/quality dashboard KPIs",
        },

        {
            "field": "axis_servo[]",
            "domain": "Axis & Servo",
            "source_mapping":
                "ZDT Axis/Servo / AIonOS normalized",
            "unit": "%",
            "purpose":
                "Per-axis load and servo condition",
        },

        {
            "field": "power_data.*",
            "domain": "Energy",
            "source_mapping":
                "ZDT PowerData / AIonOS normalized",
            "unit": "kW / kWh",
            "purpose":
                "Power and energy analytics",
        },

        {
            "field": "derived_insights[]",
            "domain": "AI Insights",
            "source_mapping": "AIonOS analytics",
            "unit": None,
            "purpose":
                "Anomaly, predictive maintenance, cycle-performance and energy-optimization insights",
        },
    ]

    dump_json(
        "data_dictionary.json",
        data_dictionary,
    )

    replay_rows = []

    replay_start = (
        datetime.fromisoformat(
            latest["EXH-R01"]["timestamp"]
        )
        - timedelta(seconds=REPLAY_SECONDS - 1)
    )

    for second in range(REPLAY_SECONDS):
        ts = replay_start + timedelta(seconds=second)
        fleet_robots = []

        for robot in ROBOTS:
            robot_id = robot["robot_id"]
            snapshot = deepcopy(
                latest[robot_id]
            )

            snapshot["timestamp"] = ts.isoformat()
            snapshot["connection_health"]["last_good_timestamp"] = (
                ts.isoformat()
            )

            phase = second % 30

            if robot_id == "EXH-R01":
                state = (
                    "RUNNING"
                    if phase < 24
                    else "READY"
                )

                axis4 = (
                    28.5
                    + 2.5 * math.sin(second / 14)
                )

                power = (
                    3.7
                    + 0.3 * math.sin(second / 10)
                )

            elif robot_id == "EXH-R02":
                state = (
                    "RUNNING"
                    if phase < 22
                    else "IDLE"
                )

                axis4 = (
                    56.0
                    + 6.0 * math.sin(second / 18)
                )

                power = (
                    4.4
                    + 0.45 * math.sin(second / 11)
                )

            else:
                state = (
                    "RUNNING"
                    if phase < 17
                    else "READY"
                )

                axis4 = (
                    31.0
                    + 3.0 * math.sin(second / 16)
                )

                power = (
                    4.9
                    + 0.55 * math.sin(second / 12)
                    if state == "RUNNING"
                    else 1.0
                )

            snapshot["live_cell"]["state"] = state
            snapshot["live_cell"]["busy"] = state == "RUNNING"

            snapshot["live_cell"]["do"]["DO_001_robot_busy"] = (
                state == "RUNNING"
            )

            snapshot["live_cell"]["do"]["DO_003_fault_active"] = False

            snapshot["live_cell"]["do"]["DO_004_robot_ready"] = (
                state in ("RUNNING", "READY")
            )

            snapshot["live_cell"]["process_values"]["override_pct"] = (
                100
                if state == "RUNNING"
                else 0
            )

            snapshot["power_data"]["instantaneous_kw"] = round(
                power,
                3,
            )

            for axis in snapshot["axis_servo"]:
                if axis["axis"] == 4:
                    axis["axis_load_pct"] = round(
                        axis4,
                        1,
                    )
                    axis["servo_indicator"] = "NORMAL"

            fleet_robots.append(
                snapshot
            )

        replay_rows.append({
            "timestamp": ts.isoformat(),
            "source_mode": "SIMULATOR",
            "robots": fleet_robots,
        })

    write_jsonl(
        "live_replay_1s.jsonl",
        replay_rows,
    )

    readme = """FANUC × AIonOS Synthetic Data V3

Multi-robot simulator dataset.

Robots
------
EXH-R01 - Assembly Robot - stable production
EXH-R02 - Handling Robot - Axis 4 anomaly + overdue predictive maintenance
EXH-R03 - Packaging Robot - cycle-performance + energy-efficiency profile

Design
------
- Current fleet state has no FAULTED robot.
- Historical fault events remain available for analytics.
- Connectivity is not an AI Insight.
- Predictive maintenance is represented inside AI Insights.
- telemetry_history.jsonl has 4,320 records per robot / 12,960 total.
- live_replay_1s.jsonl has 900 fleet snapshots.
- latest_snapshot.json remains an EXH-R01 compatibility alias.
- fleet_latest_snapshot.json is the new fleet-level source.
"""

    (OUT / "README_V3.txt").write_text(
        readme,
        encoding="utf-8",
    )

    print()
    print("MULTI-ROBOT SYNTHETIC DATA V3 CREATED")
    print("-------------------------------------")
    print(f"Output folder: {OUT}")
    print(f"Historical records: {len(history)}")
    print(f"Replay fleet snapshots: {len(replay_rows)}")
    print()

    for robot_id, snapshot in latest.items():
        print(
            robot_id,
            "|",
            snapshot["display_name"],
            "| state:",
            snapshot["live_cell"]["state"],
            "| OEE:",
            snapshot["derived_kpis"]["shift_oee_pct"],
            "| active alarms:",
            snapshot["alarms"]["active_alarm_count"],
        )


if __name__ == "__main__":
    build()
