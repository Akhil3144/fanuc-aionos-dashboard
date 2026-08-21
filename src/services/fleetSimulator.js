const STATES = ["RUNNING", "READY", "IDLE", "RUNNING", "RUNNING", "ATTENTION"];

export function simulatorMetricsFor(robot) {
  const seed = Number(robot.serialNo) || 1;
  const state = STATES[(seed - 1) % STATES.length];
  return {
    sourceMode: "SIMULATOR",
    state,
    oeePct: Number((82 + ((seed * 17) % 151) / 10).toFixed(1)),
    cycleTimeSeconds: Number((32 + ((seed * 7) % 190) / 10).toFixed(1)),
    activeAlarms: seed % 9 === 0 ? 2 : seed % 5 === 0 ? 1 : 0,
  };
}

export function simulatorSnapshotFor(registryRobot, snapshots) {
  if (!registryRobot || !snapshots?.length) return null;
  return snapshots[(registryRobot.serialNo - 1) % snapshots.length];
}

export async function loadOpenHouseCurrent() {
  const response = await fetch("/data_openhouse/robot_current.json");
  if (!response.ok) throw new Error("Open House robot simulator data is unavailable");
  return response.json();
}

export function currentMetricsFor(snapshot, robot) {
  if (!snapshot) return simulatorMetricsFor(robot);
  return {
    sourceMode: "SIMULATOR",
    state: snapshot.state,
    oeePct: snapshot.production?.oee_pct ?? snapshot.derived_kpis?.shift_oee_pct ?? 0,
    cycleTimeSeconds: snapshot.production?.actual_cycle_time_s ?? "—",
    activeAlarms: snapshot.alarms?.active_alarm_count ?? 0,
  };
}
