import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { robotRegistry } from "../src/data/robotRegistry.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataDir = path.join(root, "public", "data_openhouse");
const read = async (name) => JSON.parse(await readFile(path.join(dataDir, name), "utf8"));
const assert = (condition, message) => { if (!condition) throw new Error(message); };

const [current, production, alarms, maintenance, axes, power, insights, summary] = await Promise.all([
  "robot_current.json", "production.json", "alarms.json", "maintenance.json", "axis_servo.json",
  "power.json", "insights.json", "fleet_summary.json",
].map(read));
const ids = robotRegistry.map((robot) => robot.id);
const idSet = new Set(ids);

for (const [name, rows] of Object.entries({ current, production, maintenance, axes, power })) {
  assert(rows.length === ids.length, `${name} must contain every registry robot`);
  assert(new Set(rows.map((row) => row.robot_id)).size === ids.length, `${name} has duplicate robot IDs`);
  assert(rows.every((row) => idSet.has(row.robot_id)), `${name} has an invalid robot reference`);
}
assert([...alarms, ...insights].every((row) => idSet.has(row.robot_id)), "Alarm or insight has an invalid robot reference");
const alarmIds = new Set(alarms.map((alarm) => alarm.alarm_id));
assert(current.every((robot) => robot.alarms.active_alarm_ids.every((id) => alarmIds.has(id))), "Current data references an unknown alarm");
assert(maintenance.every((item) => item.maintenance_id.startsWith(item.robot_id)), "Maintenance reference is invalid");
for (const row of production) {
  for (const field of ["availability_pct", "performance_pct", "quality_pct", "oee_pct"]) assert(row[field] >= 0 && row[field] <= 100, `${row.robot_id} has an impossible ${field}`);
  assert(Math.abs(row.oee_pct - row.availability_pct * row.performance_pct * row.quality_pct / 10000) <= 0.11, `${row.robot_id} OEE is inconsistent`);
  assert(row.good_count_total + row.reject_count_total === row.cycle_count_total, `${row.robot_id} part counts are inconsistent`);
}
for (const id of ids) {
  const history = await read(`history/${id}.json`);
  const expected = ["OH26-R013", "OH26-R019"].includes(id) ? 120 : 24;
  assert(history.length === expected, `${id} has ${history.length}, expected ${expected} history points`);
  for (const point of history) {
    for (const field of ["availability_pct", "performance_pct", "quality_pct", "oee_pct"]) assert(point[field] >= 0 && point[field] <= 100, `${id} history has impossible ${field}`);
    assert(Math.abs(point.oee_pct - point.availability_pct * point.performance_pct * point.quality_pct / 10000) <= 0.11, `${id} history OEE is inconsistent`);
  }
}
assert(summary.total_robots === ids.length, "Fleet summary robot count is inconsistent");
console.log(JSON.stringify({ valid: true, robots: ids.length, alarms: alarms.length, maintenance: maintenance.length, insights: insights.length }, null, 2));
