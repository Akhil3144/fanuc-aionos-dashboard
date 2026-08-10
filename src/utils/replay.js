export async function loadReplayData() {
  const response = await fetch("/data/live_replay_1s.jsonl");

  if (!response.ok) {
    throw new Error("Could not load live_replay_1s.jsonl");
  }

  const text = await response.text();

  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

export function applyReplayRecord(snapshot, record) {
  if (!snapshot || !record) {
    return snapshot;
  }

  const next = structuredClone(snapshot);

  // Timestamp
  next.timestamp = record.timestamp;

  // Robot state
  next.live_cell.state = record.state;
  next.live_cell.busy = record.state === "RUNNING";

  // Keep digital outputs consistent with state
  next.live_cell.do.DO_001_robot_busy =
    record.state === "RUNNING";

  next.live_cell.do.DO_003_fault_active =
    record.state === "FAULTED";

  next.live_cell.do.DO_004_robot_ready =
    record.state === "READY";

  // Production
  next.production.cycle_count_total =
    record.cycle_count_total;

  next.live_cell.registers.R_001_cycle_count =
    record.cycle_count_total;

  // Axis 4 live load
  const axis4 = next.axis_servo.find(
    (axis) => axis.axis === 4
  );

  if (axis4) {
    axis4.axis_load_pct = record.axis_4_load_pct;

    if (record.axis_4_load_pct >= 85) {
      axis4.servo_indicator = "ALERT";
    } else if (record.axis_4_load_pct >= 70) {
      axis4.servo_indicator = "WATCH";
    } else {
      axis4.servo_indicator = "NORMAL";
    }
  }

  // Current power
  next.power_data.instantaneous_kw =
    record.instantaneous_kw;

  // Active alarms
  const activeIds =
    record.active_alarm_ids || [];

  next.alarms.active_alarm_ids = activeIds;
  next.alarms.active_alarm_count =
    activeIds.length;

  // Connection health
  next.connection_health.edge_connection =
    record.connection_health;

  next.connection_health.stale =
    record.connection_health !== "CONNECTED";

  next.connection_health.data_quality =
    record.connection_health === "CONNECTED"
      ? "GOOD"
      : "STALE";

  if (record.connection_health === "CONNECTED") {
    next.connection_health.last_good_timestamp = record.timestamp;
  }

  return next;
}
