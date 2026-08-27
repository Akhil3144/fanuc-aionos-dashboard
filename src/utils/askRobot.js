const ASK_ROBOT_API = `${import.meta.env.VITE_API_BASE_URL || "https://roboinsight-api.onrender.com"}/ask-my-robot`;
const ASK_ROBOT_TIMEOUT_MS = 30000;


export async function askMyRobot(
  question,
  liveSnapshot = null,
  options = {}
) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), ASK_ROBOT_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(ASK_ROBOT_API, {
      method: "POST",
      signal: controller.signal,

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        question,
        live_snapshot:
          liveSnapshot,
        selected_registry_id:
          options.selectedRegistryId || null,
        selected_robot_id:
          options.selectedRobotId || liveSnapshot?.robot_id || null,
        robot_id:
          options.selectedRobotId || liveSnapshot?.robot_id || null,
        scope:
          options.scope || "ROBOT",
        robot_registry:
          options.registry || [],
      }),
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("The intelligence service took too long to respond. Please retry.", { cause: error });
    }
    throw new Error("The intelligence service is unavailable. Please retry.", { cause: error });
  } finally {
    window.clearTimeout(timeout);
  }


  if (!response.ok) {
    let message =
      `Ask My Robot failed: ${response.status}`;

    try {
      const error =
        await response.json();

      if (error.detail) {
        message =
          error.detail;
      }
    } catch {
      // Keep default error message.
    }

    throw new Error(
      message
    );
  }


  return response.json();
}
