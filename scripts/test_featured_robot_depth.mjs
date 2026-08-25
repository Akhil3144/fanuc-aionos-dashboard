import assert from "node:assert/strict";
import fs from "node:fs";
import { robotRegistry } from "../src/data/robotRegistry.js";

const read = (path) => JSON.parse(fs.readFileSync(new URL(path, import.meta.url)));
const current = read("../public/data_openhouse/robot_current.json");
const alarms = read("../public/data_openhouse/alarms.json");
const maintenance = read("../public/data_openhouse/maintenance.json");
const insights = read("../public/data_openhouse/insights.json");

for (const id of ["OH26-R013", "OH26-R019"]) {
  const robot = robotRegistry.find((item) => item.id === id);
  const snapshot = current.find((item) => item.robot_id === id);
  const history = read(`../public/data_openhouse/history/${id}.json`);
  assert.equal(robot.featured, true, `${id} featured`);
  assert.equal(history.length, 120, `${id} history depth`);
  assert.ok(snapshot.production?.oee_pct != null && snapshot.production?.availability_pct != null && snapshot.production?.target_cycle_time_s != null, `${id} performance fields`);
  assert.equal(snapshot.axis_servo?.length, 6, `${id} J1-J6`);
  for (let axis = 1; axis <= 6; axis += 1) assert.ok(history.some((point) => Number.isFinite(Number(point[`axis${axis}_load_pct`]))), `${id} J${axis} history`);
  assert.ok(snapshot.power_data?.instantaneous_kw != null && snapshot.power_data?.kwh_total != null, `${id} energy fields`);
  assert.ok(alarms.some((item) => item.robot_id === id), `${id} alarm evidence`);
  assert.ok(maintenance.some((item) => item.robot_id === id), `${id} maintenance evidence`);
  assert.ok(insights.some((item) => item.robot_id === id), `${id} insight evidence`);
}

assert.equal(robotRegistry.find((item) => item.id === "OH26-R001").featured, false, "normal robot remains non-featured");
console.log("Featured robot depth: PASS · R013/R019 fields and J1-J6 history resolve · R001 remains normal.");
