const COLLABORATIVE_ALIASES = ["collaborative robot", "collaborative robots", "collaborative", "cobot", "cobots"];

export function isCrxRobot(robot) {
  return String(robot?.model || "").toUpperCase().includes("CRX");
}

export function robotMatchesFleetSearch(robot, search) {
  const query = String(search || "").trim().toLowerCase();
  if (!query) return true;
  if (COLLABORATIVE_ALIASES.some((alias) => query.includes(alias))) return isCrxRobot(robot);
  return [robot.id, robot.serialNo, robot.model, robot.application, robot.ipAddress, robot.location]
    .some((value) => String(value || "").toLowerCase().includes(query));
}
