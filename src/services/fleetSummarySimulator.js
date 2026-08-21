// Synthetic fallback only. Runtime pages load the generated Open House simulator dataset.
export const fleetSummarySimulator = Object.freeze({
  sourceMode: "SIMULATOR",
  utilizationPct: 87.6,
  running: 23,
  readyIdle: 5,
  critical: 2,
  throughput: 128540,
  averageCyclePerformancePct: 94.8,
  targetAchievementPct: 92.4,
  healthy: 23,
  attention: 5,
  reliabilityPct: 96.7,
  activeAlarms: 7,
  criticalAlarms: 2,
  maintenanceDue: 3,
  currentFleetPowerKw: 94.2,
  energyPerCycleKwh: 0.73,
  applicationTypes: 11,
  attentionRobots: 5,
});

export async function loadFleetSummarySimulator() {
  const response = await fetch("/data_openhouse/fleet_summary.json");
  if (!response.ok) throw new Error("Open House fleet summary is unavailable");
  const data = await response.json();
  return {
    sourceMode: "SIMULATOR",
    totalRobots: data.total_robots,
    utilizationPct: Number((((data.running + data.ready) / data.total_robots) * 100).toFixed(1)),
    running: data.running,
    readyIdle: data.ready + data.idle,
    critical: data.critical,
    throughput: data.total_cycles,
    averageCyclePerformancePct: data.fleet_performance_pct,
    targetAchievementPct: data.fleet_quality_pct,
    healthy: data.healthy,
    attention: data.attention,
    reliabilityPct: data.fleet_availability_pct,
    activeAlarms: data.active_alarms,
    criticalAlarms: data.critical,
    maintenanceDue: data.maintenance_due + data.maintenance_overdue,
    currentFleetPowerKw: data.current_fleet_power_kw,
    energyPerCycleKwh: Number((data.total_fleet_energy_kwh / Math.max(data.total_cycles, 1)).toFixed(2)),
    attentionRobots: data.attention + data.critical,
  };
}
