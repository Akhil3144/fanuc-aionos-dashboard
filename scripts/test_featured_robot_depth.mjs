import assert from "node:assert/strict";
import fs from "node:fs";
import { robotRegistry } from "../src/data/robotRegistry.js";

const read = (path) => JSON.parse(fs.readFileSync(new URL(path, import.meta.url)));
const current = read("../public/data_openhouse/robot_current.json");
const alarms = read("../public/data_openhouse/alarms.json");
const maintenance = read("../public/data_openhouse/maintenance.json");
const insights = read("../public/data_openhouse/insights.json");

assert.deepEqual(robotRegistry.filter((robot) => robot.featured).map((robot) => robot.id), ["OH26-R013", "OH26-R019"]);
assert.equal(robotRegistry.find((robot) => robot.id === "OH26-R041").featured, false);

for (const id of robotRegistry.filter((item) => item.featured).map((item) => item.id)) {
  const robot = robotRegistry.find((item) => item.id === id);
  const snapshot = current.find((item) => item.robot_id === id);
  const history = read(`../public/data_openhouse/history/${id}.json`);
  assert.equal(robot.featured, true, `${id} featured`);
  assert.equal(history.length, 120, `${id} history depth`);
  assert.ok(snapshot.production?.oee_pct != null && snapshot.production?.availability_pct != null && snapshot.production?.target_cycle_time_s != null, `${id} performance fields`);
  assert.equal(snapshot.axis_servo?.length, 6, `${id} J1-J6`);
  for (let axis = 1; axis <= 6; axis += 1) assert.ok(history.some((point) => Number.isFinite(Number(point[`axis${axis}_load_pct`]))), `${id} J${axis} history`);
  assert.ok(snapshot.power_data?.instantaneous_kw != null && snapshot.power_data?.kwh_total != null, `${id} energy fields`);
  assert.ok(maintenance.some((item) => item.robot_id === id), `${id} maintenance evidence`);
  assert.ok(Array.isArray(alarms.filter((item) => item.robot_id === id)), `${id} alarm collection`);
  assert.ok(Array.isArray(insights.filter((item) => item.robot_id === id)), `${id} insight collection`);
}

assert.equal(robotRegistry.find((item) => item.id === "OH26-R006").featured, false, "normal robot remains non-featured");
console.log("Featured robot depth: PASS · all featured fields and J1-J6 history resolve · R006 remains normal.");
