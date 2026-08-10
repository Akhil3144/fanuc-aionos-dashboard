const ASK_ROBOT_API =
  "http://127.0.0.1:8000/ask-my-robot";


export async function askMyRobot(
  question,
  liveSnapshot = null
) {
  const response = await fetch(
    ASK_ROBOT_API,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        question,
        live_snapshot:
          liveSnapshot,
      }),
    }
  );


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