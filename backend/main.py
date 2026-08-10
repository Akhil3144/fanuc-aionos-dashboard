from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ask_routes import router as ask_router


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "public" / "data"
TELEMETRY_FILE = DATA_DIR / "telemetry_history.jsonl"


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

    return value.astimezone(IST)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="FANUC × AIonOS Analytics API",
    version="1.2.0",
    description=(
        "Read-only analytics backend for the "
        "FANUC exhibition simulator."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://roboinsight.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask_router)

# ============================================================
# DUCKDB HELPERS
# ============================================================

def get_connection():
    return duckdb.connect(
        database=":memory:"
    )


def telemetry_source():
    path = (
        TELEMETRY_FILE
        .as_posix()
        .replace("'", "''")
    )

    return f"read_ndjson_auto('{path}')"


def check_dataset():
    if not TELEMETRY_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "Telemetry file not found: "
                f"{TELEMETRY_FILE}"
            ),
        )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "service":
            "FANUC × AIonOS Analytics API",

        "status":
            "running",

        "mode":
            "SIMULATOR",

        "read_only":
            True,

        "timezone":
            "Asia/Kolkata",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    check_dataset()

    con = get_connection()

    try:
        result = con.execute(
            f"""
            SELECT
                COUNT(*) AS record_count,
                MIN(timestamp) AS first_timestamp,
                MAX(timestamp) AS last_timestamp

            FROM {telemetry_source()}
            """
        ).fetchone()

        return {
            "status":
                "healthy",

            "dataset":
                TELEMETRY_FILE.name,

            "record_count":
                result[0],

            "first_timestamp":
                to_ist(result[1]),

            "last_timestamp":
                to_ist(result[2]),

            "timezone":
                "Asia/Kolkata",

            "sample_interval_seconds":
                60,
        }

    finally:
        con.close()


# ============================================================
# ANALYTICS OVERVIEW
# ============================================================

@app.get("/analytics/overview")
def analytics_overview():
    check_dataset()

    con = get_connection()

    try:

        overview = con.execute(
            f"""
            SELECT
                COUNT(*) AS telemetry_records,

                MIN(timestamp) AS start_time,
                MAX(timestamp) AS end_time,

                MIN(
                    production.cycle_count_total
                ) AS first_cycle_count,

                MAX(
                    production.cycle_count_total
                ) AS last_cycle_count,

                SUM(
                    production.cycles_completed_this_minute
                ) AS cycles_produced,

                ROUND(
                    AVG(
                        CASE
                            WHEN
                                production.actual_cycle_time_s > 0
                            THEN
                                production.actual_cycle_time_s
                        END
                    ),
                    2
                ) AS average_cycle_time_s,

                ROUND(
                    MAX(
                        production.actual_cycle_time_s
                    ),
                    2
                ) AS maximum_cycle_time_s,

                ROUND(
                    MIN(
                        production.actual_cycle_time_s
                    ),
                    2
                ) AS minimum_cycle_time_s,

                COUNT(*)
                FILTER (
                    WHERE live_cell.state = 'RUNNING'
                ) AS running_records,

                COUNT(*)
                FILTER (
                    WHERE live_cell.state = 'IDLE'
                ) AS idle_records,

                COUNT(*)
                FILTER (
                    WHERE live_cell.state = 'READY'
                ) AS ready_records,

                COUNT(*)
                FILTER (
                    WHERE live_cell.state = 'FAULTED'
                ) AS fault_records,

                COUNT(*)
                FILTER (
                    WHERE connection_health.stale = TRUE
                ) AS stale_connection_records,

                ROUND(
                    AVG(
                        power_data.instantaneous_kw
                    ),
                    2
                ) AS average_power_kw,

                ROUND(
                    MAX(
                        power_data.instantaneous_kw
                    ),
                    2
                ) AS peak_power_kw,

                ROUND(
                    MAX(
                        power_data.kwh_total
                    )
                    -
                    MIN(
                        power_data.kwh_total
                    ),
                    2
                ) AS energy_used_kwh

            FROM {telemetry_source()}
            """
        ).fetchone()


        # ====================================================
        # HIGHEST HISTORICAL AXIS LOAD
        # ====================================================

        highest_axis = con.execute(
            f"""
            SELECT
                axis_data.axis AS axis,

                ROUND(
                    MAX(
                        axis_data.axis_load_pct
                    ),
                    2
                ) AS maximum_load_pct

            FROM
                {telemetry_source()} AS telemetry,

                UNNEST(
                    telemetry.axis_servo
                ) AS axis_table(axis_data)

            GROUP BY
                axis_data.axis

            ORDER BY
                maximum_load_pct DESC

            LIMIT 1
            """
        ).fetchone()


        # ====================================================
        # LATEST HISTORICAL STATE
        # ====================================================

        latest = con.execute(
            f"""
            SELECT
                timestamp,
                shift,

                live_cell.state,

                robot_status.working_status,
                robot_status.process_status,
                robot_status.mechanical_status,

                alarms.active_alarm_count,

                connection_health.edge_connection,
                connection_health.data_quality,

                derived_kpis.shift_oee_pct

            FROM {telemetry_source()}

            ORDER BY timestamp DESC

            LIMIT 1
            """
        ).fetchone()


        return {
            "dataset": {
                "records":
                    overview[0],

                "start_time":
                    to_ist(overview[1]),

                "end_time":
                    to_ist(overview[2]),

                "timezone":
                    "Asia/Kolkata",

                "sample_interval_seconds":
                    60,
            },

            "production": {
                "first_cycle_count":
                    overview[3],

                "last_cycle_count":
                    overview[4],

                "cycles_produced":
                    overview[5],

                "average_cycle_time_s":
                    overview[6],

                "maximum_cycle_time_s":
                    overview[7],

                "minimum_cycle_time_s":
                    overview[8],
            },

            "state_time_minutes": {
                "running":
                    overview[9],

                "idle":
                    overview[10],

                "ready":
                    overview[11],

                "faulted":
                    overview[12],
            },

            "connectivity": {
                "stale_minutes":
                    overview[13],
            },

            "energy": {
                "average_power_kw":
                    overview[14],

                "peak_power_kw":
                    overview[15],

                "energy_used_kwh":
                    overview[16],
            },

            "axis": {
                "highest_load_axis":
                    highest_axis[0]
                    if highest_axis
                    else None,

                "highest_load_pct":
                    highest_axis[1]
                    if highest_axis
                    else None,
            },

            "latest": {
                "timestamp":
                    to_ist(latest[0]),

                "shift":
                    latest[1],

                "state":
                    latest[2],

                "working_status":
                    latest[3],

                "process_status":
                    latest[4],

                "mechanical_status":
                    latest[5],

                "active_alarm_count":
                    latest[6],

                "edge_connection":
                    latest[7],

                "data_quality":
                    latest[8],

                "shift_oee_pct":
                    latest[9],
            },
        }

    finally:
        con.close()


# ============================================================
# HISTORICAL TRENDS
# ============================================================

@app.get("/analytics/trends")
def analytics_trends(
    hours: int = Query(
        default=24,
        ge=1,
        le=72,
    ),

    bucket_minutes: int = Query(
        default=15
    ),
):

    check_dataset()

    allowed_buckets = {
        5,
        15,
        30,
        60,
    }

    if bucket_minutes not in allowed_buckets:
        raise HTTPException(
            status_code=400,
            detail=(
                "bucket_minutes must be one of "
                "5, 15, 30 or 60"
            ),
        )

    con = get_connection()

    try:

        # ====================================================
        # WINDOW INFORMATION
        # ====================================================

        window = con.execute(
            f"""
            WITH telemetry AS (

                SELECT *

                FROM {telemetry_source()}
            ),

            bounds AS (

                SELECT
                    MAX(timestamp) AS max_timestamp

                FROM telemetry
            )

            SELECT

                MIN(t.timestamp)
                    AS start_timestamp,

                MAX(t.timestamp)
                    AS end_timestamp,

                COUNT(*)
                    AS record_count

            FROM telemetry t,
                 bounds b

            WHERE
                t.timestamp >
                b.max_timestamp
                - INTERVAL '{hours} hours'
            """
        ).fetchone()


        # ====================================================
        # TREND QUERY
        # ====================================================

        rows = con.execute(
            f"""
            WITH telemetry AS (

                SELECT *

                FROM {telemetry_source()}
            ),

            bounds AS (

                SELECT
                    MAX(timestamp) AS max_timestamp

                FROM telemetry
            ),

            filtered AS (

                SELECT
                    t.*

                FROM telemetry t,
                     bounds b

                WHERE
                    t.timestamp >
                    b.max_timestamp
                    - INTERVAL '{hours} hours'
            ),

            axis4 AS (

                SELECT
                    f.timestamp,

                    MAX(
                        axis_data.axis_load_pct
                    ) AS axis_4_load_pct

                FROM
                    filtered f,

                    UNNEST(
                        f.axis_servo
                    ) AS axis_table(
                        axis_data
                    )

                WHERE
                    axis_data.axis = 4

                GROUP BY
                    f.timestamp
            )

            SELECT

                time_bucket(
                    INTERVAL '{bucket_minutes} minutes',
                    f.timestamp
                ) AS bucket_start,


                -- -------------------------------------------
                -- PRODUCTION
                -- -------------------------------------------

                ROUND(
                    AVG(
                        CASE
                            WHEN
                                f.production.actual_cycle_time_s
                                > 0

                            THEN
                                f.production.actual_cycle_time_s
                        END
                    ),
                    2
                ) AS average_cycle_time_s,


                SUM(
                    f.production.cycles_completed_this_minute
                ) AS cycles_completed,


                -- -------------------------------------------
                -- POWER
                -- -------------------------------------------

                ROUND(
                    AVG(
                        f.power_data.instantaneous_kw
                    ),
                    2
                ) AS average_power_kw,


                ROUND(
                    MAX(
                        f.power_data.instantaneous_kw
                    ),
                    2
                ) AS peak_power_kw,


                -- -------------------------------------------
                -- AXIS 4
                -- -------------------------------------------

                ROUND(
                    AVG(
                        a.axis_4_load_pct
                    ),
                    2
                ) AS average_axis_4_load_pct,


                ROUND(
                    MAX(
                        a.axis_4_load_pct
                    ),
                    2
                ) AS maximum_axis_4_load_pct,


                -- -------------------------------------------
                -- ROBOT STATE MINUTES
                -- -------------------------------------------

                COUNT(*)
                FILTER (
                    WHERE
                        f.live_cell.state = 'RUNNING'
                ) AS running_minutes,


                COUNT(*)
                FILTER (
                    WHERE
                        f.live_cell.state = 'IDLE'
                ) AS idle_minutes,


                COUNT(*)
                FILTER (
                    WHERE
                        f.live_cell.state = 'READY'
                ) AS ready_minutes,


                COUNT(*)
                FILTER (
                    WHERE
                        f.live_cell.state = 'FAULTED'
                ) AS faulted_minutes,


                -- -------------------------------------------
                -- OEE
                -- -------------------------------------------

                ROUND(
                    AVG(
                        f.derived_kpis.shift_oee_pct
                    ),
                    2
                ) AS average_shift_oee_pct,


                -- -------------------------------------------
                -- ALARMS / CONNECTIVITY
                -- -------------------------------------------

                MAX(
                    f.alarms.active_alarm_count
                ) AS maximum_active_alarms,


                COUNT(*)
                FILTER (
                    WHERE
                        f.connection_health.stale = TRUE
                ) AS stale_minutes


            FROM filtered f

            LEFT JOIN axis4 a
                ON f.timestamp = a.timestamp


            GROUP BY
                bucket_start


            ORDER BY
                bucket_start
            """
        ).fetchall()


        # ====================================================
        # SERIALIZE TREND POINTS
        # ====================================================

        data = []

        for row in rows:

            data.append({
                "timestamp":
                    to_ist(row[0]),

                "average_cycle_time_s":
                    row[1],

                "cycles_completed":
                    row[2],

                "average_power_kw":
                    row[3],

                "peak_power_kw":
                    row[4],

                "average_axis_4_load_pct":
                    row[5],

                "maximum_axis_4_load_pct":
                    row[6],

                "running_minutes":
                    row[7],

                "idle_minutes":
                    row[8],

                "ready_minutes":
                    row[9],

                "faulted_minutes":
                    row[10],

                "average_shift_oee_pct":
                    row[11],

                "maximum_active_alarms":
                    row[12],

                "stale_minutes":
                    row[13],
            })


        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "window": {
                "requested_hours":
                    hours,

                "bucket_minutes":
                    bucket_minutes,

                "source_records":
                    window[2],

                "start_time":
                    to_ist(window[0]),

                "end_time":
                    to_ist(window[1]),

                "timezone":
                    "Asia/Kolkata",
            },

            "points":
                len(data),

            "data":
                data,
        }

    finally:
        con.close()