import { findRegistryRobot, robotRegistry } from "../data/robotRegistry.js";

export function resolveChatContext(pathname) {
  const match = String(pathname || "").match(/^\/robot\/([^/]+)/);
  const robot = match ? findRegistryRobot(decodeURIComponent(match[1])) : null;
  return { scope: robot ? "ROBOT" : "FLEET", robotId: robot?.id || null, registryRobot: robot, robots: robotRegistry };
}
