import assert from "node:assert/strict";
import fs from "node:fs";
import { robotRegistry } from "../src/data/robotRegistry.js";
import { isCrxRobot, robotMatchesFleetSearch } from "../src/utils/fleetSearch.js";
import { resolveChatContext } from "../src/utils/chatContext.js";

assert.equal(robotRegistry.length, 36);
const crx = robotRegistry.filter(isCrxRobot);
assert.equal(crx.length, 16);
for (const query of ["Collaborative Robot", "collaborative", "cobot", "CRX"]) {
  const matches = robotRegistry.filter((robot) => robotMatchesFleetSearch(robot, query));
  assert.deepEqual(matches.map((robot) => robot.id), crx.map((robot) => robot.id), query);
  assert.equal(matches.some((robot) => !isCrxRobot(robot)), false, `${query} false positive`);
}
for (const [path, scope, robotId] of [["/", "FLEET", null], ["/fleet", "FLEET", null], ["/robot/OH26-R013", "ROBOT", "OH26-R013"], ["/robot/OH26-R019", "ROBOT", "OH26-R019"]]) {
  assert.deepEqual({ scope: resolveChatContext(path).scope, robotId: resolveChatContext(path).robotId }, { scope, robotId });
}
const current = JSON.parse(fs.readFileSync(new URL("../public/data_openhouse/robot_current.json", import.meta.url)));
for (const robot of robotRegistry) {
  const snapshot = current.find((item) => item.robot_id === robot.id);
  assert.ok(snapshot, `${robot.id} current data`);
  assert.equal(snapshot.robot_name, robot.model, `${robot.id} model consistency`);
  assert.equal(snapshot.role, robot.application, `${robot.id} application consistency`);
}
for (const id of ["OH26-R013", "OH26-R019"]) {
  const snapshot = current.find((item) => item.robot_id === id);
  assert.ok(snapshot.production?.oee_pct != null && snapshot.power_data?.instantaneous_kw != null && snapshot.axis_servo?.length, `${id} featured evidence`);
}
console.log(`Client enhancements: PASS · ${crx.length} CRX robots · chat contexts and 36 registry identities verified.`);
