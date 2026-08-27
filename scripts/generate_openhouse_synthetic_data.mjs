import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { robotRegistry } from "../src/data/robotRegistry.js";
import { registerDefinitions } from "../src/data/registerDefinitions.js";

const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT_DIR = path.join(PROJECT_ROOT, "public", "data_openhouse");
const HISTORY_DIR = path.join(OUTPUT_DIR, "history");
const BASE_TIME = Date.parse("2026-08-21T10:00:00+05:30");

function hashSeed(text) {
  let hash = 2166136261;
  for (const character of text) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function generator(seedText) {
  let state = hashSeed(seedText) || 1;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

const round = (value, digits = 1) => Number(value.toFixed(digits));
const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));
const timestamp = (milliseconds) => new Date(milliseconds).toISOString();

function applicationProfile(robot) {
  const text = `${robot.application || ""} ${robot.model}`.toLowerCase();
  if (/pallet|rtu|m-900|r-2000|m-710/.test(text)) return { scale: "HEAVY", power: 10.5, load: 48, target: 56 };
  if (/weld|arc|cladding/.test(text)) return { scale: "WELDING", power: 8.2, load: 40, target: 48 };
  if (/paint/.test(text)) return { scale: "PAINTING", power: 6.7, load: 34, target: 52 };
  if (/vision|error proof|inspection|rtvt/.test(text)) return { scale: "INSPECTION", power: 2.8, load: 20, target: 31 };
  if (/pick|packag|order fulfil|label/.test(text)) return { scale: "FAST_PICK", power: 4.2, load: 29, target: 25 };
  if (/crx|collaborative|lr-mate/.test(text)) return { scale: "LIGHT", power: 3.5, load: 25, target: 39 };
  return { scale: "GENERAL", power: 5.2, load: 33, target: 45 };
}

function healthFor(robot) {
  if ([9, 28].includes(robot.serialNo)) return { health: "CRITICAL", state: robot.serialNo === 9 ? "FAULTED" : "IDLE" };
  if ([13, 19, 20, 25, 31].includes(robot.serialNo)) return { health: "ATTENTION", state: robot.serialNo === 25 ? "IDLE" : "RUNNING" };
  const states = ["RUNNING", "RUNNING", "RUNNING", "READY", "RUNNING", "IDLE"];
  return { health: "NORMAL", state: states[robot.serialNo % states.length] };
}

function createRobotData(robot) {
  const random = generator(robot.id);
  const profile = applicationProfile(robot);
  const { health, state } = healthFor(robot);
  const isR013 = robot.id === "OH26-R013";
  const isR019 = robot.id === "OH26-R019";
  const connection = robot.serialNo === 9 ? "OFFLINE" : robot.serialNo === 28 ? "STALE" : "CONNECTED";

  let availability = 96.2 + random() * 3;
  let performance = 92.5 + random() * 5;
  let quality = 98.2 + random() * 1.7;
  if (health === "ATTENTION") { availability -= 2.2; performance -= 2.5; }
  if (health === "CRITICAL") { availability -= 9; performance -= 7; quality -= 1.5; }
  if (isR013) { availability = 97.1; performance = 96.2; quality = 99.4; }
  if (isR019) { availability = 93.4; performance = 96.3; quality = 99.1; }
  availability = round(clamp(availability, 75, 99.8));
  performance = round(clamp(performance, 75, 99.5));
  quality = round(clamp(quality, 94, 99.9));
  const oee = round((availability * performance * quality) / 10000);

  const targetCycle = round(profile.target + (random() - 0.5) * 7);
  const cycleDeviation = health === "CRITICAL" ? 0.15 : health === "ATTENTION" ? 0.07 : 0.025;
  const actualCycle = state === "RUNNING" ? round(targetCycle * (1 + cycleDeviation + (random() - 0.5) * 0.02)) : null;
  const cycleCount = 1800 + robot.serialNo * 137 + Math.floor(random() * 900);
  const rejects = Math.max(1, Math.round(cycleCount * (1 - quality / 100)));
  const good = cycleCount - rejects;
  const plannedTime = 240000 + robot.serialNo * 900;
  const faultedTime = Math.round(plannedTime * (1 - availability / 100));
  const operatingTime = plannedTime - faultedTime;
  const runningRate = clamp(0.55 + performance / 250 + (random() - 0.5) * 0.08, 0.55, 0.94);
  const runningTime = Math.round(operatingTime * runningRate);
  const idleTime = Math.round((operatingTime - runningTime) * 0.58);
  const readyTime = operatingTime - runningTime - idleTime;

  const axes = Array.from({ length: 6 }, (_, index) => {
    const axis = index + 1;
    let axisLoad = profile.load + [2, 8, 5, 13, 7, 1][index] + (random() - 0.5) * 9;
    if (isR013 && axis === 4) axisLoad = 47.8;
    if (isR019 && axis === 2) axisLoad = 72.4;
    if (health === "CRITICAL" && axis === 3) axisLoad += 20;
    axisLoad = round(clamp(axisLoad, 8, 91));
    const errorCount = isR019 && axis === 2 ? 4 : health === "CRITICAL" && axis === 3 ? 6 : random() > 0.88 ? 1 : 0;
    return {
      axis,
      axis_load_pct: axisLoad,
      error_count: errorCount,
      odometer: round(42000 + robot.serialNo * 5300 + axis * 8100 + random() * 4000),
      servo_indicator: errorCount >= 5 ? "CRITICAL" : errorCount > 0 || axisLoad > 70 ? "ATTENTION" : "NORMAL",
    };
  });

  let instantaneousKw = profile.power * (state === "RUNNING" ? 1 : state === "FAULTED" ? 0.25 : 0.45) * (0.92 + random() * 0.18);
  if (isR019) instantaneousKw = 13.8;
  instantaneousKw = round(instantaneousKw, 2);
  const kwhTotal = round(350 + robot.serialNo * 41 + profile.power * 62 + random() * 120, 2);
  const power = {
    instantaneous_kw: instantaneousKw,
    kwh_total: kwhTotal,
    kwh_run: round(kwhTotal * 0.84, 2),
    kwh_idle: round(kwhTotal * 0.105, 2),
    kwh_fault: round(kwhTotal * 0.015, 2),
    kwh_regen: round(kwhTotal * 0.04, 2),
  };

  const activeAlarm = isR013 || isR019 || health === "CRITICAL" || robot.serialNo % 11 === 0;
  const alarmId = `${robot.id}-ALM-${String(100 + robot.serialNo).padStart(3, "0")}`;
  const alarm = activeAlarm ? {
    alarm_id: alarmId,
    robot_id: robot.id,
    severity: health === "CRITICAL" ? "HIGH" : "MEDIUM",
    alarm_type: isR013 ? "PROCESS" : isR019 ? "SERVO" : health === "CRITICAL" ? "MECHANICAL" : "PROCESS",
    category: isR013 ? "PROCESS" : isR019 ? "SERVO" : health === "CRITICAL" ? "MECHANICAL" : "PROCESS",
    message: isR013 ? "Inspection cycle deviation above observation band" : isR019 ? "Intermittent Axis 2 servo deviation" : "Operational condition requires review",
    status: "ACTIVE",
    started_at: timestamp(BASE_TIME - (18 + robot.serialNo) * 60000),
    cleared_at: null,
  } : null;
  const clearedAlarm = robot.serialNo % 4 === 0 ? {
    alarm_id: `${robot.id}-ALM-H${robot.serialNo}`,
    robot_id: robot.id,
    severity: "LOW",
    alarm_type: "PROCESS",
    category: "PROCESS",
    message: "Transient process interlock",
    status: "CLEARED",
    started_at: timestamp(BASE_TIME - 18 * 3600000),
    cleared_at: timestamp(BASE_TIME - 18 * 3600000 + 420000),
  } : null;

  let maintenanceStatus = "OK";
  if (isR013 || robot.serialNo === 11 || robot.serialNo === 31) maintenanceStatus = "DUE_SOON";
  if (isR019 || health === "CRITICAL") maintenanceStatus = "OVERDUE";
  const remainingHours = maintenanceStatus === "OVERDUE" ? -(12 + robot.serialNo) : maintenanceStatus === "DUE_SOON" ? 36 + robot.serialNo : 220 + robot.serialNo * 9;
  const maintenance = {
    maintenance_id: `${robot.id}-MNT-01`,
    robot_id: robot.id,
    component: isR013 ? "Axis 4 drive train" : isR019 ? "Axis 2 servo assembly" : "Controller and mechanical inspection",
    title: isR013 ? "Axis 4 drive-train inspection" : isR019 ? "Axis 2 servo inspection" : "Scheduled robot inspection",
    description: isR013 ? "Inspect the Axis 4 drive train alongside the observed load trend." : isR019 ? "Inspect the Axis 2 servo assembly and review recent servo deviations." : "Complete the scheduled condition inspection.",
    status: maintenanceStatus,
    priority: maintenanceStatus === "OVERDUE" ? "HIGH" : maintenanceStatus === "DUE_SOON" ? "MEDIUM" : "LOW",
    interval_hours: profile.scale === "HEAVY" ? 750 : 1000,
    remaining_hours: remainingHours,
    service_due: timestamp(BASE_TIME + remainingHours * 3600000),
    recommended_action: isR013 ? "Inspect Axis 4 during the next planned maintenance window." : isR019 ? "Prioritize the overdue Axis 2 servo inspection." : "Continue the scheduled inspection plan.",
  };

  const production = {
    robot_id: robot.id,
    shift: "OPEN_HOUSE",
    target_cycle_time_s: targetCycle,
    actual_cycle_time_s: actualCycle,
    cycle_count_total: cycleCount,
    good_count_total: good,
    reject_count_total: rejects,
    running_time_s: runningTime,
    idle_time_s: idleTime,
    ready_time_s: readyTime,
    faulted_time_s: faultedTime,
    running_rate: round(runningTime / plannedTime, 4),
    availability_pct: availability,
    performance_pct: performance,
    quality_pct: quality,
    oee_pct: oee,
    shift_availability_pct: availability,
    shift_performance_pct: performance,
    shift_quality_pct: quality,
    shift_oee_pct: oee,
  };

  const current = {
    robot_id: robot.id,
    timestamp: timestamp(BASE_TIME),
    state,
    connection_health: connection,
    working_status: health,
    process_status: isR013 ? "ATTENTION" : health,
    mechanical_status: health,
    mode: "AUTO",
    program: `${profile.scale}_${String(robot.serialNo).padStart(2, "0")}`,
    override_pct: state === "FAULTED" ? 0 : health === "CRITICAL" ? 65 : 100,
    source_mode: "SIMULATOR",
    robot_name: robot.model,
    display_name: robot.model,
    role: robot.application,
    shift: "OPEN_HOUSE",
    connection_health_detail: { edge_connection: connection, data_quality: connection === "CONNECTED" ? "GOOD" : "DEGRADED", stale: connection !== "CONNECTED", latency_ms: connection === "CONNECTED" ? 18 + robot.serialNo : null },
    live_cell: { state, busy: state === "RUNNING", process_values: { program: `${profile.scale}_${String(robot.serialNo).padStart(2, "0")}`, mode: "AUTO", override_pct: state === "FAULTED" ? 0 : 100 }, do: { DO_001_robot_busy: state === "RUNNING", DO_004_robot_ready: state === "READY" || state === "RUNNING" }, di: { DI_002_part_present: state === "RUNNING" } },
    production,
    derived_kpis: { shift_availability_pct: availability, shift_performance_pct: performance, shift_quality_pct: quality, shift_oee_pct: oee },
    robot_status: { working_status: health, process_status: isR013 ? "ATTENTION" : health, mechanical_status: health },
    alarms: { active_alarm_ids: alarm ? [alarmId] : [], active_alarm_count: alarm ? 1 : 0 },
    axis_servo: axes,
    power_data: power,
  };

  const sampleCount = robot.featured ? 120 : 24;
  const intervalMs = robot.featured ? 60000 : 300000;
  const historyRandom = generator(`${robot.id}:history`);
  const history = Array.from({ length: sampleCount }, (_, index) => {
    const progress = sampleCount === 1 ? 1 : index / (sampleCount - 1);
    const wave = Math.sin(index / 4.5) * 0.7;
    const r013Trend = isR013 ? progress * 3.2 : 0;
    const r019Pulse = isR019 && index > 82 && index < 91 ? 5.5 : 0;
    const samplePerformance = round(clamp(performance + wave - r013Trend * 0.45 + (historyRandom() - 0.5) * 0.35, 70, 99.8));
    const sampleAvailability = round(clamp(availability + Math.sin(index / 9) * 0.35 - (r019Pulse ? 0.8 : 0), 70, 99.9));
    const sampleQuality = round(clamp(quality + (historyRandom() - 0.5) * 0.18, 94, 100));
    const sampleOee = round((sampleAvailability * samplePerformance * sampleQuality) / 10000);
    const cycle = round(targetCycle * (1 + cycleDeviation * 0.45 + r013Trend / 100 + wave / 100 + r019Pulse / 180));
    const axisLoads = axes.map((axis) => round(clamp(axis.axis_load_pct + Math.sin(index / (5 + axis.axis)) * 2 + (isR013 && axis.axis === 4 ? progress * 6 - 3 : 0) + (isR019 && axis.axis === 2 ? r019Pulse : 0), 5, 96)));
    const sampleState = isR019 && index === 87 ? "FAULTED" : isR013 && index % 41 === 0 ? "IDLE" : state === "FAULTED" && index < sampleCount - 3 ? "READY" : state;
    return {
      timestamp: timestamp(BASE_TIME - (sampleCount - 1 - index) * intervalMs),
      state: sampleState,
      cycle_time_s: sampleState === "RUNNING" ? cycle : null,
      cycle_deviation_pct: sampleState === "RUNNING" ? round(((cycle - targetCycle) / targetCycle) * 100) : null,
      availability_pct: sampleAvailability,
      performance_pct: samplePerformance,
      quality_pct: sampleQuality,
      oee_pct: sampleOee,
      axis1_load_pct: axisLoads[0], axis2_load_pct: axisLoads[1], axis3_load_pct: axisLoads[2],
      axis4_load_pct: axisLoads[3], axis5_load_pct: axisLoads[4], axis6_load_pct: axisLoads[5],
      servo_error_count: axes.reduce((sum, axis) => sum + axis.error_count, 0) + (isR019 && index % 29 === 0 ? 1 : 0),
      power_kw: round(clamp(instantaneousKw + Math.sin(index / 6) * profile.power * 0.08 + r019Pulse / 4, 0.2, 25), 2),
      active_alarm_count: (isR013 && index >= sampleCount - 12) || (isR019 && index >= 87 && index <= 91) ? 1 : 0,
      active_alarm_ids: (isR013 && index >= sampleCount - 12) || (isR019 && index >= 87 && index <= 91) ? [alarmId] : [],
      mechanical_status: isR013 && index >= sampleCount - 15 ? "ATTENTION" : isR019 && index >= 87 ? "ATTENTION" : health,
      maintenance_status: maintenanceStatus,
    };
  });

  const insights = [];
  if (isR013) {
    insights.push(
      { insight_id: "OH26-R013-INS-01", robot_id: robot.id, category: "CYCLE_DEGRADATION", severity: "MEDIUM", title: "Recent cycle-time increase", evidence: "Cycle time rises gradually across the later 1-minute samples while quality remains stable.", recommendation: "Inspect process timing and the Axis 4 drive train during the next planned window." },
      { insight_id: "OH26-R013-INS-02", robot_id: robot.id, category: "AXIS_LOAD_TREND", severity: "MEDIUM", title: "Axis 4 load trend", evidence: "Axis 4 load increases gradually in the later history and coincides with cycle deviation.", recommendation: "Review Axis 4 load and servo condition; do not infer causation without inspection." },
      { insight_id: "OH26-R013-INS-03", robot_id: robot.id, category: "MAINTENANCE_DUE", severity: "MEDIUM", title: "Axis 4 inspection due soon", evidence: `Maintenance ${maintenance.maintenance_id} is DUE_SOON with ${remainingHours} hours remaining.`, recommendation: maintenance.recommended_action },
    );
  } else if (isR019) {
    insights.push(
      { insight_id: "OH26-R019-INS-01", robot_id: robot.id, category: "POWER_ANOMALY", severity: "MEDIUM", title: "Elevated fleet power", evidence: `Current power is ${instantaneousKw} kW, consistent with the larger RTU application but above most fleet robots.`, recommendation: "Review power alongside production state before classifying efficiency." },
      { insight_id: "OH26-R019-INS-02", robot_id: robot.id, category: "ALARM_PATTERN", severity: "HIGH", title: "Axis 2 servo event window", evidence: "The recent alarm window coincides with higher Axis 2 load and intermittent servo error counts.", recommendation: "Prioritize the overdue Axis 2 servo inspection; correlation is not confirmed cause." },
      { insight_id: "OH26-R019-INS-03", robot_id: robot.id, category: "MAINTENANCE_DUE", severity: "HIGH", title: "Axis 2 inspection overdue", evidence: `Maintenance ${maintenance.maintenance_id} is OVERDUE by ${Math.abs(remainingHours)} hours.`, recommendation: maintenance.recommended_action },
    );
  } else if (health !== "NORMAL") {
    insights.push({ insight_id: `${robot.id}-INS-01`, robot_id: robot.id, category: "HEALTH_ATTENTION", severity: health === "CRITICAL" ? "HIGH" : "MEDIUM", title: "Robot condition requires review", evidence: `Latest mechanical status is ${health}.`, recommendation: "Review current alarms and maintenance evidence before action." });
  }

  return { current, production, axes: { robot_id: robot.id, axes }, power: { robot_id: robot.id, ...power }, alarms: [alarm, clearedAlarm].filter(Boolean), maintenance, insights, history };
}

async function writeJson(filePath, value) {
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function main() {
  await mkdir(HISTORY_DIR, { recursive: true });
  const generated = robotRegistry.map(createRobotData);
  const current = generated.map((item) => item.current);
  const production = generated.map((item) => item.production);
  const alarms = generated.flatMap((item) => item.alarms);
  const maintenance = generated.map((item) => item.maintenance);
  const axisServo = generated.map((item) => item.axes);
  const power = generated.map((item) => item.power);
  const insights = generated.flatMap((item) => item.insights);

  const totalCycles = production.reduce((sum, item) => sum + item.cycle_count_total, 0);
  const goodParts = production.reduce((sum, item) => sum + item.good_count_total, 0);
  const rejects = production.reduce((sum, item) => sum + item.reject_count_total, 0);
  const weight = (field) => round(production.reduce((sum, item) => sum + item[field] * item.cycle_count_total, 0) / totalCycles);
  const fleetAvailability = weight("availability_pct");
  const fleetPerformance = weight("performance_pct");
  const fleetQuality = round((goodParts / (goodParts + rejects)) * 100);
  const fleetOee = round((fleetAvailability * fleetPerformance * fleetQuality) / 10000);
  const fleetSummary = {
    timestamp: timestamp(BASE_TIME), source_mode: "SIMULATOR", total_robots: current.length,
    running: current.filter((item) => item.state === "RUNNING").length,
    ready: current.filter((item) => item.state === "READY").length,
    idle: current.filter((item) => item.state === "IDLE").length,
    faulted: current.filter((item) => item.state === "FAULTED").length,
    connected: current.filter((item) => item.connection_health === "CONNECTED").length,
    stale: current.filter((item) => item.connection_health === "STALE").length,
    offline: current.filter((item) => item.connection_health === "OFFLINE").length,
    healthy: current.filter((item) => item.mechanical_status === "NORMAL").length,
    attention: current.filter((item) => item.mechanical_status === "ATTENTION").length,
    critical: current.filter((item) => item.mechanical_status === "CRITICAL").length,
    active_alarms: current.reduce((sum, item) => sum + item.alarms.active_alarm_count, 0),
    maintenance_due: maintenance.filter((item) => item.status === "DUE_SOON").length,
    maintenance_overdue: maintenance.filter((item) => item.status === "OVERDUE").length,
    total_cycles: totalCycles, good_parts: goodParts, rejects,
    fleet_availability_pct: fleetAvailability, fleet_performance_pct: fleetPerformance,
    fleet_quality_pct: fleetQuality, fleet_oee_pct: fleetOee,
    current_fleet_power_kw: round(power.reduce((sum, item) => sum + item.instantaneous_kw, 0), 2),
    total_fleet_energy_kwh: round(power.reduce((sum, item) => sum + item.kwh_total, 0), 2),
  };

  await Promise.all([
    writeJson(path.join(OUTPUT_DIR, "fleet_summary.json"), fleetSummary),
    writeJson(path.join(OUTPUT_DIR, "robot_registry.json"), robotRegistry),
    writeJson(path.join(OUTPUT_DIR, "register_definitions.json"), registerDefinitions),
    writeJson(path.join(OUTPUT_DIR, "robot_current.json"), current),
    writeJson(path.join(OUTPUT_DIR, "production.json"), production),
    writeJson(path.join(OUTPUT_DIR, "alarms.json"), alarms),
    writeJson(path.join(OUTPUT_DIR, "maintenance.json"), maintenance),
    writeJson(path.join(OUTPUT_DIR, "axis_servo.json"), axisServo),
    writeJson(path.join(OUTPUT_DIR, "power.json"), power),
    writeJson(path.join(OUTPUT_DIR, "insights.json"), insights),
    writeJson(path.join(OUTPUT_DIR, "telemetry_history.json"), { history_files: robotRegistry.map((robot) => `history/${robot.id}.json`) }),
    ...generated.map((item) => writeJson(path.join(HISTORY_DIR, `${item.current.robot_id}.json`), item.history)),
  ]);

  console.log(JSON.stringify({ robots: current.length, normal: robotRegistry.filter((item) => !item.featured).length, featured: robotRegistry.filter((item) => item.featured).length, normalHistoryPoints: 24, featuredHistoryPoints: 120, activeAlarms: fleetSummary.active_alarms, maintenanceDue: fleetSummary.maintenance_due, maintenanceOverdue: fleetSummary.maintenance_overdue, fleetOee: fleetSummary.fleet_oee_pct, fleetPower: fleetSummary.current_fleet_power_kw }, null, 2));
}

await main();
