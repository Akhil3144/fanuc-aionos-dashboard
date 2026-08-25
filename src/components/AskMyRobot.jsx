import { useEffect, useRef, useState } from "react";
import { askMyRobot } from "../utils/askRobot";
import "./AskMyRobot.css";
import AITag from "./AITag";

const FLEET_QUESTIONS = [
  "Which robots need the most attention?",
  "Which robots have overdue maintenance?",
  "Which robot has the lowest OEE?",
  "Which robot has the highest axis load?",
  "Which robots have active alarms?",
  "Give me an overall fleet condition summary.",
];
const NORMAL_QUESTIONS = [
  "Give me a condition summary.", "What is the current OEE?", "Which axis has the highest load?",
  "Are there active alarms?", "Is maintenance due?", "How is current cycle performance?",
];
const FEATURED_QUESTIONS = [
  "How far is cycle time from target?", "Which axis has the highest load?", "What maintenance is due?",
  "How does current power compare with history?", "Is OEE above or below its historical average?",
  "Give me a complete condition summary.", "What changed recently?", "What should be inspected first?",
  "Explain the latest alarm in context.",
];

function welcomeMessage(robotId, scope) {
  return {
    role: "assistant",
    text:
      (scope === "fleet" ? "Scope: all Open House 2026 robots. " : `Selected robot: ${robotId || "—"}. `) +
      "Ask about fleet configuration and operational intelligence.",
  };
}

export default function AskMyRobot({
  snapshot,
  robotId,
  selectedRobotId,
  robots = [],
  registry = [],
  registryRobot = null,
  scope = "robot",
}) {
  const normalizedScope = String(scope || "ROBOT").toUpperCase();
  const activeRobotId =
    (normalizedScope === "FLEET" ? "ALL ROBOTS" : (robotId || selectedRobotId)) ||
    snapshot?.robot_id ||
    "";
  const suggestedQuestions = normalizedScope === "FLEET" ? FLEET_QUESTIONS : registryRobot?.featured ? FEATURED_QUESTIONS : NORMAL_QUESTIONS;

  const [question, setQuestion] =
    useState("");

  const [messages, setMessages] =
    useState([
      welcomeMessage(activeRobotId, normalizedScope.toLowerCase()),
    ]);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState(null);

  const inputRef = useRef(null);

  useEffect(() => {
    setMessages([
      welcomeMessage(activeRobotId, normalizedScope.toLowerCase()),
    ]);

    setQuestion("");
    setError(null);
  }, [activeRobotId, normalizedScope]);

  async function submitQuestion(
    questionOverride = null
  ) {
    const text = (
      questionOverride ??
      question
    ).trim();

    if (!text || loading) {
      return;
    }

    setError(null);

    setMessages(
      (current) => [
        ...current,
        {
          role: "user",
          text,
        },
      ]
    );

    setQuestion("");
    setLoading(true);

    try {
      const response =
        await askMyRobot(
          text,
          snapshot,
          {
            selectedRegistryId: registryRobot?.id || null,
            selectedRobotId: robotId || selectedRobotId || snapshot?.robot_id || null,
            scope: normalizedScope,
            registry,
          }
        );

      const displayScope =
        response.query_scope ===
        "FLEET_COMPARISON"
          ? "FLEET"
          : (
              response.selected_robot_id ||
              activeRobotId
            );

      setMessages(
        (current) => [
          ...current,
          {
            role: "assistant",

            text:
              response.answer ||
              "No grounded answer was returned.",

            meta: {
              context:
                displayScope,

              readOnly:
                response.read_only,

              queryScope:
                response.query_scope,
            },
          },
        ]
      );
    } catch (err) {
      console.error(
        "Ask My Robot error:",
        err
      );

      setError(
        err.message ||
        "Ask My Robot is unavailable."
      );

      setMessages(
        (current) => [
          ...current,
          {
            role: "assistant",

            text:
              "I could not retrieve a grounded answer from the robot analytics service.",

            error: true,
          },
        ]
      );
    } finally {
      setLoading(false);

      setTimeout(
        () => {
          inputRef.current?.focus();
        },
        50
      );
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitQuestion();
  }

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      submitQuestion();
    }
  }

  function clearConversation() {
    setMessages([
      welcomeMessage(activeRobotId, scope),
    ]);

    setError(null);
    setQuestion("");

    setTimeout(
      () => {
        inputRef.current?.focus();
      },
      50
    );
  }

  return (
    <article className="ask-robot-panel">

      <div className="ask-robot-header">
        <div>
          <span className="panel-eyebrow">
            AIonOS Intelligence
          </span>

          <h2>
            Ask My Robot <AITag />
          </h2>

          <p>
            Ask about the Open House fleet and operational intelligence.
          </p>
        </div>

        <div className="ask-robot-header-actions">
          <span className="ask-readonly-chip">
            READ ONLY
          </span>
        </div>
      </div>

      <div className="ask-context-strip">
        <div>
          <span>
            Selected robot
          </span>

          <strong>
            {scope === "fleet" ? "ALL ROBOTS" : activeRobotId || "—"}
          </strong>
        </div>

        <div>
          <span>
            Robot name
          </span>

          <strong>
            {
              registryRobot?.model || snapshot?.display_name ||
              snapshot?.robot_name ||
              "—"
            }
          </strong>
        </div>

        <div>
          <span>
            Current state
          </span>

          <strong>
            {
              scope === "fleet" ? "FLEET" : snapshot
                ?.live_cell
                ?.state ||
              "—"
            }
          </strong>
        </div>

        <div>
          <span>
            Fleet
          </span>

          <strong>
            {registry.length || robots.length} robots
          </strong>
        </div>

        <div>
          <span>
            Evidence
          </span>

          <strong>
            Question-aware
          </strong>
        </div>
      </div>

      <div className="ask-suggestions">
        {suggestedQuestions.map(
          (item) => (
            <button
              key={item}
              type="button"
              disabled={loading}
              onClick={() =>
                submitQuestion(item)
              }
            >
              {item}
            </button>
          )
        )}
      </div>

      <div className="ask-conversation">
        {messages.map(
          (message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                `ask-message ask-message-${message.role} ${
                  message.error
                    ? "ask-message-error"
                    : ""
                }`
              }
            >
              <div className="ask-message-label">
                {
                  message.role ===
                  "assistant"
                    ? "ASK MY ROBOT"
                    : "YOU"
                }
              </div>

              <div className="ask-message-body">
                {message.text}
              </div>

              {message.meta && (
                <div className="ask-message-meta">

                  {message.meta.context && (
                    <span>
                      {message.meta.context}
                    </span>
                  )}

                  {message.meta.queryScope && (
                    <span>
                      {message.meta.queryScope}
                    </span>
                  )}

                  {message.meta.readOnly && (
                    <span>
                      READ ONLY
                    </span>
                  )}

                </div>
              )}
            </div>
          )
        )}

        {loading && (
          <div className="ask-message ask-message-assistant">

            <div className="ask-message-label">
              ASK MY ROBOT
            </div>

            <div className="ask-thinking">
              <span></span>
              <span></span>
              <span></span>

              <small>
                Analysing robot evidence…
              </small>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="ask-error">
          {error}
        </div>
      )}

      <form
        className="ask-input-area"
        onSubmit={handleSubmit}
      >
        <textarea
          ref={inputRef}

          value={question}

          onChange={(event) =>
            setQuestion(
              event.target.value
            )
          }

          onKeyDown={handleKeyDown}

          disabled={loading}

          rows={1}

          maxLength={500}

          placeholder={
            normalizedScope === "FLEET" ? "Ask about the Open House robot fleet..." : `Ask about ${activeRobotId || "the selected robot"}...`
          }
        />

        <button
          type="submit"

          disabled={
            loading ||
            !question.trim()
          }

          className="ask-send-button"
        >
          {
            loading
              ? "Analysing…"
              : "Ask"
          }
        </button>
      </form>

      <div className="ask-robot-footer">
        <span>
          Open House fleet intelligence · Read only
        </span>

        <button
          type="button"
          onClick={clearConversation}
        >
          Clear
        </button>
      </div>

    </article>
  );
}
