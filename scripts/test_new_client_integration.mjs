import assert from "node:assert/strict";
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { robotRegistry } from "../src/data/robotRegistry.js";
import { imageForRobot } from "../src/data/robotImages.js";
import { registerDefinitions } from "../src/data/registerDefinitions.js";
import { robotMatchesFleetSearch } from "../src/utils/fleetSearch.js";

const workbook = new URL("../data_source/Robot list v1.xlsx", import.meta.url);
const sharedStrings = execFileSync("unzip", ["-p", fileURLToPath(workbook), "xl/sharedStrings.xml"], { encoding: "utf8" });
for (const term of ["CRX ZONE", "TECH CENTER", "FUSION HUB", "CRX-3iA", "R-2000iC/210F", "R-2000/210F-31E", "10.31.58.82"]) {
  assert.ok(sharedStrings.toUpperCase().includes(term.toUpperCase()), `workbook contains ${term}`);
}

assert.equal(robotRegistry.length, 36);
assert.equal(new Set(robotRegistry.map((robot) => robot.id)).size, 36);
assert.deepEqual(Object.fromEntries(["CRX ZONE", "TECH CENTER", "FUSION HUB"].map((zone) => [zone, robotRegistry.filter((robot) => robot.zone === zone).length])), { "CRX ZONE": 11, "TECH CENTER": 19, "FUSION HUB": 6 });
assert.equal(robotRegistry.filter((robot) => robot.ipAddress).length, 20);
assert.equal(robotRegistry.filter((robot) => !robot.ipAddress).length, 16);

const collaborative = robotRegistry.filter((robot) => robotMatchesFleetSearch(robot, "Collaborative Robot"));
assert.equal(collaborative.length, 16);
assert.ok(collaborative.every((robot) => robot.model.toUpperCase().includes("CRX")));
for (const query of ["CRX", "AI Error Proofing", "Flexible Spot Welding", "FUSION HUB", "TECH CENTER", "R-2000iC/210F"]) {
  assert.ok(robotRegistry.some((robot) => robotMatchesFleetSearch(robot, query)), `${query} search`);
}

let exact = 0;
for (const robot of robotRegistry) {
  const image = imageForRobot(robot);
  if (!image.isPlaceholder) {
    exact += 1;
    assert.ok(fs.existsSync(new URL(`../public${decodeURIComponent(image.src)}`, import.meta.url)), `${robot.model} image exists`);
  }
}
assert.equal(exact, 33);

assert.equal(registerDefinitions.AI_ERROR_PROOFING.registers.length, 10);
assert.deepEqual(registerDefinitions.AI_ERROR_PROOFING.registers.map((item) => item.index), [11, 12, 13, 14, 15, 16, 17, 19, 20, 21]);
assert.deepEqual(registerDefinitions.FLEXIBLE_SPOT_WELDING_R2000IC_210F.registers.map((item) => item.index), Array.from({ length: 17 }, (_, index) => index + 21));
assert.deepEqual(registerDefinitions.FLEXIBLE_SPOT_WELDING_R2000_210F_31E.registers.map((item) => item.index), Array.from({ length: 17 }, (_, index) => index + 51));
for (const schema of Object.values(registerDefinitions)) assert.ok(schema.registers.every((item) => item.currentValue === null && item.valueSource === "UNAVAILABLE"));

console.log(`New client integration: PASS · 36 robots · ${collaborative.length} CRX · ${exact} exact tile mappings · no fabricated register values.`);
