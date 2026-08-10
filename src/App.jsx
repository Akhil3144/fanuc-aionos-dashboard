import { useEffect, useMemo, useState } from "react";
import "./App.css";
import AskMyRobot from "./components/AskMyRobot";

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Unable to load ${url}`);
  }
  return response.json();
}

function tone(value) {
  const v = String(value || "").toUpperCase();

  if (
    v.includes("HIGH") ||
    v.includes("OVERDUE") ||
    v.includes("FAULT") ||
    v.includes("CRITICAL")
  ) {
    return "danger";
  }

  if (
    v.includes("ATTENTION") ||
    v.includes("MEDIUM") ||
    v.includes("DUE_SOON") ||
    v.includes("WATCH") ||
    v.includes("IDLE")
  ) {
    return "warning";
  }

  return "success";
}

function Dot({ value = "NORMAL" }) {
  return (
    <span className={`compact-dot compact-${tone(value)}`} />
  );
}

function MiniMetric({ label, value, helper }) {
  return (
    <div className="compact-mini-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {helper && <small>{helper}</small>}
    </div>
  );
}

function App() {
  const [fleetRobots, setFleetRobots] = useState([]);
  const [selectedRobotId, setSelectedRobotId] = useState("");
  const [snapshot, setSnapshot] = useState(null);
  const [shiftSummary, setShiftSummary] = useState([]);
  const [allAlarms, setAllAlarms] = useState([]);
  const [allMaintenance, setAllMaintenance] = useState([]);
  const [allInsights, setAllInsights] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      loadJson("/data_v3/fleet_latest_snapshot.json"),
      loadJson("/data_v3/production_shift_summary.json"),
      loadJson("/data_v3/alarms.json"),
      loadJson("/data_v3/maintenance.json"),
      loadJson("/data_v3/derived_insights.json"),
    ])
      .then(
        ([
          fleetData,
          shiftData,
          alarmData,
          maintenanceData,
          insightData,
        ]) => {
          const robots = Array.isArray(fleetData?.robots)
            ? fleetData.robots
            : [];

          if (!robots.length) {
            throw new Error("No robots found in V3 data.");
          }

          const stored = localStorage.getItem(
            "fanucSelectedRobotId"
          );

          const initialId = robots.some(
            (robot) => robot.robot_id === stored
          )
            ? stored
            : robots[0].robot_id;

          const initialSnapshot =
            robots.find(
              (robot) => robot.robot_id === initialId
            ) || robots[0];

          setFleetRobots(robots);
          setSelectedRobotId(initialId);
          setSnapshot(initialSnapshot);
          setShiftSummary(
            Array.isArray(shiftData) ? shiftData : []
          );
          setAllAlarms(
            Array.isArray(alarmData) ? alarmData : []
          );
          setAllMaintenance(
            Array.isArray(maintenanceData)
              ? maintenanceData
              : []
          );
          setAllInsights(
            Array.isArray(insightData) ? insightData : []
          );
        }
      )
      .catch((err) => {
        console.error(err);
        setError(err.message);
      });
  }, []);

  const selectRobot = (event) => {
    const id = event.target.value;
    setSelectedRobotId(id);
    localStorage.setItem("fanucSelectedRobotId", id);

    const next = fleetRobots.find(
      (robot) => robot.robot_id === id
    );

    if (next) {
      setSnapshot(next);
    }
  };

  const selectedAlarms = useMemo(() => {
    if (!selectedRobotId) return [];

    const activeIds =
      snapshot?.alarms?.active_alarm_ids || [];

    return allAlarms
      .filter(
        (alarm) => alarm.robot_id === selectedRobotId
      )
      .map((alarm) => ({
        ...alarm,
        status: activeIds.includes(alarm.alarm_id)
          ? "ACTIVE"
          : alarm.status === "ACTIVE"
            ? "CLEARED"
            : alarm.status,
      }));
  }, [allAlarms, selectedRobotId, snapshot]);

  const selectedMaintenance = useMemo(
    () =>
      allMaintenance.filter(
        (item) => item.robot_id === selectedRobotId
      ),
    [allMaintenance, selectedRobotId]
  );

  const selectedInsights = useMemo(
    () =>
      allInsights.filter(
        (item) =>
          item.robot_id === selectedRobotId &&
          item.category !== "CONNECTIVITY"
      ),
    [allInsights, selectedRobotId]
  );

  const currentShift = useMemo(() => {
    if (!snapshot) return null;

    return (
      shiftSummary.find(
        (item) =>
          item.robot_id === snapshot.robot_id &&
          item.shift === snapshot.shift
      ) ||
      shiftSummary.find(
        (item) => item.robot_id === snapshot.robot_id
      ) ||
      null
    );
  }, [snapshot, shiftSummary]);

  if (!snapshot && !error) {
    return (
      <div className="boot-screen">
        <strong>Loading multi-robot dashboard…</strong>
      </div>
    );
  }

  if (error) {
    return <div className="error-banner">{error}</div>;
  }

  const production = snapshot.production || {};
  const health = snapshot.robot_status || {};
  const axes = snapshot.axis_servo || [];
  const power = snapshot.power_data || {};
  const activeAlarms = selectedAlarms.filter(
    (alarm) => alarm.status === "ACTIVE"
  );

  const highestAxis = axes.length
    ? axes.reduce((best, axis) =>
        axis.axis_load_pct > best.axis_load_pct
          ? axis
          : best
      )
    : null;

  const totalServoErrors = axes.reduce(
    (sum, axis) => sum + Number(axis.error_count || 0),
    0
  );

  const predictiveAlerts = selectedInsights.filter(
    (item) =>
      item.category === "PREDICTIVE_MAINTENANCE" ||
      item.category === "ANOMALY"
  ).length;

  const oee =
    currentShift?.shift_oee_pct ??
    currentShift?.oee_pct ??
    snapshot.derived_kpis?.shift_oee_pct ??
    "—";

  const availability =
    currentShift?.availability_pct ??
    snapshot.derived_kpis?.shift_availability_pct ??
    "—";

  const performance =
    currentShift?.performance_pct ??
    snapshot.derived_kpis?.shift_performance_pct ??
    "—";

  const quality =
    currentShift?.quality_pct ??
    snapshot.derived_kpis?.shift_quality_pct ??
    "—";

  const maintenanceDue = selectedMaintenance.filter(
    (item) =>
      item.status === "OVERDUE" ||
      item.status === "DUE_SOON"
  );

  return (
    <div className="compact-dashboard">
      <style>{`
        .compact-dashboard {
          min-height: 100vh;
        }

        .compact-dashboard * {
          box-sizing: border-box;
        }

        .compact-top {
          max-width: 1480px;
          margin: 0 auto;
          padding: 14px 28px 10px;
        }

        .compact-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 10px;
        }

        .compact-brand-kicker {
          font-size: 10px;
          letter-spacing: .22em;
          text-transform: uppercase;
          opacity: .7;
          margin-bottom: 3px;
        }

        .compact-header h1 {
          margin: 0;
          font-size: clamp(24px, 2.2vw, 34px);
          line-height: 1.05;
        }

        .compact-header p {
          margin: 5px 0 0;
          font-size: 12px;
          opacity: .6;
        }

        .compact-controls {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
          justify-content: flex-end;
        }

        .compact-select-wrap {
          display: flex;
          align-items: center;
          gap: 8px;
          border: 1px solid rgba(255,255,255,.12);
          border-radius: 10px;
          padding: 5px 9px;
          min-height: 38px;
        }

        .compact-select-wrap span {
          font-size: 9px;
          letter-spacing: .14em;
          text-transform: uppercase;
          opacity: .55;
        }

        .compact-select-wrap select {
          background: transparent;
          color: inherit;
          border: 0;
          outline: 0;
          font-size: 13px;
          font-weight: 700;
          min-width: 235px;
        }

        .compact-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          border: 1px solid rgba(255,255,255,.12);
          border-radius: 999px;
          padding: 8px 10px;
          font-size: 9px;
          letter-spacing: .1em;
          text-transform: uppercase;
          white-space: nowrap;
        }

        .compact-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          display: inline-block;
          flex: 0 0 auto;
          background: currentColor;
          box-shadow: 0 0 8px currentColor;
        }

        .compact-success {
          color: #56d9a0;
        }

        .compact-warning {
          color: #e7bc55;
        }

        .compact-danger {
          color: #f06d72;
        }

        .compact-kpis {
          display: grid;
          grid-template-columns: repeat(6, minmax(0, 1fr));
          gap: 8px;
          margin-bottom: 8px;
        }

        .compact-mini-metric {
          min-height: 61px;
          border: 1px solid rgba(255,255,255,.10);
          border-radius: 10px;
          padding: 8px 10px;
          background: rgba(255,255,255,.018);
        }

        .compact-mini-metric > span {
          display: block;
          font-size: 8px;
          letter-spacing: .13em;
          text-transform: uppercase;
          opacity: .5;
          margin-bottom: 4px;
        }

        .compact-mini-metric > strong {
          display: block;
          font-size: 18px;
          line-height: 1.1;
        }

        .compact-mini-metric > small {
          display: block;
          margin-top: 3px;
          font-size: 8px;
          opacity: .48;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .compact-evidence-grid {
          display: grid;
          grid-template-columns: 1.05fr 1fr 1.25fr 1.65fr;
          gap: 8px;
          align-items: stretch;
        }

        .compact-card {
          border: 1px solid rgba(255,255,255,.10);
          border-radius: 12px;
          padding: 10px 11px;
          background: rgba(255,255,255,.018);
          min-width: 0;
          height: 224px;
          overflow: hidden;
        }

        .compact-card-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          margin-bottom: 7px;
        }

        .compact-card-head h2 {
          margin: 0;
          font-size: 13px;
        }

        .compact-card-head span {
          font-size: 8px;
          letter-spacing: .11em;
          text-transform: uppercase;
          opacity: .46;
        }

        .compact-stat-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 6px;
        }

        .compact-stat {
          border: 1px solid rgba(255,255,255,.07);
          border-radius: 8px;
          padding: 7px;
          min-width: 0;
        }

        .compact-stat span {
          display: block;
          font-size: 8px;
          opacity: .5;
          margin-bottom: 3px;
        }

        .compact-stat strong {
          display: block;
          font-size: 13px;
        }

        .compact-list {
          display: grid;
          gap: 5px;
        }

        .compact-list-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          min-height: 24px;
          border-bottom: 1px solid rgba(255,255,255,.06);
          font-size: 9px;
        }

        .compact-list-row:last-child {
          border-bottom: 0;
        }

        .compact-list-row > span:first-child {
          opacity: .58;
        }

        .compact-list-row strong {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 10px;
        }

        .compact-axis-list {
          display: grid;
          gap: 4px;
          margin-top: 6px;
        }

        .compact-axis-row {
          display: grid;
          grid-template-columns: 22px 1fr 37px;
          gap: 6px;
          align-items: center;
          font-size: 8px;
        }

        .compact-axis-track {
          height: 4px;
          border-radius: 999px;
          background: rgba(255,255,255,.08);
          overflow: hidden;
        }

        .compact-axis-fill {
          display: block;
          height: 100%;
          border-radius: inherit;
          background: currentColor;
        }

        .compact-evidence-head {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 6px;
          margin-bottom: 6px;
        }

        .compact-alert-box {
          border: 1px solid rgba(255,255,255,.07);
          border-radius: 8px;
          padding: 7px;
        }

        .compact-alert-box > span {
          display: block;
          font-size: 8px;
          opacity: .5;
          margin-bottom: 3px;
          text-transform: uppercase;
          letter-spacing: .08em;
        }

        .compact-alert-box strong {
          font-size: 12px;
        }

        .compact-insights {
          display: grid;
          gap: 5px;
        }

        .compact-insight {
          border-top: 1px solid rgba(255,255,255,.07);
          padding-top: 5px;
        }

        .compact-insight:first-child {
          border-top: 0;
          padding-top: 0;
        }

        .compact-insight-top {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          align-items: center;
          margin-bottom: 2px;
        }

        .compact-insight-top span {
          font-size: 7px;
          letter-spacing: .09em;
          text-transform: uppercase;
          opacity: .55;
        }

        .compact-insight strong {
          display: block;
          font-size: 9px;
          line-height: 1.25;
          margin-bottom: 2px;
        }

        .compact-insight p {
          margin: 0;
          font-size: 8px;
          line-height: 1.25;
          opacity: .63;
        }

        .compact-action {
          margin-top: 2px !important;
        }

        .compact-action b {
          font-weight: 700;
          opacity: .9;
        }

        .compact-ai {
          max-width: 1480px;
          margin: 0 auto;
          padding: 8px 28px 24px;
          scroll-margin-top: 10px;
        }

        .compact-ai-label {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin: 2px 0 6px;
        }

        .compact-ai-label strong {
          font-size: 11px;
          letter-spacing: .12em;
          text-transform: uppercase;
        }

        .compact-ai-label span {
          font-size: 9px;
          opacity: .55;
        }

        .compact-ai .ask-robot-panel {
          margin-top: 0 !important;
        }

        @media (min-width: 1050px) {
          .compact-top {
            min-height: 48vh;
            max-height: 570px;
          }
        }

        @media (max-width: 1100px) {
          .compact-kpis {
            grid-template-columns: repeat(3, 1fr);
          }

          .compact-evidence-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .compact-card {
            height: auto;
            min-height: 210px;
          }
        }

        @media (max-width: 720px) {
          .compact-top,
          .compact-ai {
            padding-left: 14px;
            padding-right: 14px;
          }

          .compact-header {
            align-items: flex-start;
            flex-direction: column;
          }

          .compact-controls {
            justify-content: flex-start;
          }

          .compact-kpis,
          .compact-evidence-grid {
            grid-template-columns: 1fr 1fr;
          }

          .compact-select-wrap select {
            min-width: 190px;
          }
        }
      `}</style>

      <section className="compact-top">
        <header className="compact-header">
          <div>
            <div className="compact-brand-kicker">
              FANUC × AIonOS
            </div>

            <h1>Exhibition Cell Intelligence</h1>

            <p>
              Selected robot evidence above · AI questioning directly below.
            </p>
          </div>

          <div className="compact-controls">
            <label className="compact-select-wrap">
              <span>Robot</span>

              <select
                value={selectedRobotId}
                onChange={selectRobot}
              >
                {fleetRobots.map((robot) => (
                  <option
                    key={robot.robot_id}
                    value={robot.robot_id}
                  >
                    {robot.robot_id} —{" "}
                    {robot.display_name || robot.robot_name}
                  </option>
                ))}
              </select>
            </label>

            <span className="compact-chip">
              <Dot value="NORMAL" />
              CONNECTED
            </span>

            <span className="compact-chip">
              SIMULATOR
            </span>

            <span className="compact-chip">
              READ ONLY
            </span>
          </div>
        </header>

        <div className="compact-kpis">
          <MiniMetric
            label="Robot Status"
            value={snapshot.live_cell?.state || "—"}
            helper={snapshot.display_name}
          />

          <MiniMetric
            label="Shift OEE"
            value={`${oee}%`}
            helper={`Shift ${snapshot.shift}`}
          />

          <MiniMetric
            label="Total Cycles"
            value={Number(
              production.cycle_count_total || 0
            ).toLocaleString("en-IN")}
            helper="Accumulated"
          />

          <MiniMetric
            label="Active Alarms"
            value={activeAlarms.length}
            helper={
              activeAlarms.length
                ? "Needs review"
                : "No active alarm"
            }
          />

          <MiniMetric
            label="Predictive Alerts"
            value={predictiveAlerts}
            helper={`${maintenanceDue.length} maintenance item(s) due`}
          />

          <MiniMetric
            label="Current Power"
            value={`${Number(
              power.instantaneous_kw || 0
            ).toFixed(2)} kW`}
            helper={`${Number(
              power.kwh_total || 0
            ).toFixed(1)} kWh total`}
          />
        </div>

        <div className="compact-evidence-grid">
          <article className="compact-card">
            <div className="compact-card-head">
              <h2>Production</h2>
              <span>ZDT Production</span>
            </div>

            <div className="compact-stat-grid">
              <div className="compact-stat">
                <span>Target cycle</span>
                <strong>
                  {production.target_cycle_time_s ?? "—"}s
                </strong>
              </div>

              <div className="compact-stat">
                <span>Current cycle</span>
                <strong>
                  {production.actual_cycle_time_s != null
                    ? `${production.actual_cycle_time_s}s`
                    : "Not cycling"}
                </strong>
              </div>

              <div className="compact-stat">
                <span>Availability</span>
                <strong>{availability}%</strong>
              </div>

              <div className="compact-stat">
                <span>Performance</span>
                <strong>{performance}%</strong>
              </div>

              <div className="compact-stat">
                <span>Quality</span>
                <strong>{quality}%</strong>
              </div>

              <div className="compact-stat">
                <span>Running rate</span>
                <strong>
                  {(
                    Number(production.running_rate || 0) * 100
                  ).toFixed(1)}
                  %
                </strong>
              </div>
            </div>
          </article>

          <article className="compact-card">
            <div className="compact-card-head">
              <h2>Robot Health</h2>
              <span>ZDT RobotStatus</span>
            </div>

            <div className="compact-list">
              <div className="compact-list-row">
                <span>Working</span>
                <strong>
                  <Dot value={health.working_status} />
                  {health.working_status || "—"}
                </strong>
              </div>

              <div className="compact-list-row">
                <span>Process</span>
                <strong>
                  <Dot value={health.process_status} />
                  {health.process_status || "—"}
                </strong>
              </div>

              <div className="compact-list-row">
                <span>Mechanical</span>
                <strong>
                  <Dot value={health.mechanical_status} />
                  {health.mechanical_status || "—"}
                </strong>
              </div>

              <div className="compact-list-row">
                <span>Robot busy</span>
                <strong>
                  {snapshot.live_cell?.do
                    ?.DO_001_robot_busy
                    ? "ON"
                    : "OFF"}
                </strong>
              </div>

              <div className="compact-list-row">
                <span>Robot ready</span>
                <strong>
                  {snapshot.live_cell?.do
                    ?.DO_004_robot_ready
                    ? "ON"
                    : "OFF"}
                </strong>
              </div>

              <div className="compact-list-row">
                <span>Part present</span>
                <strong>
                  {snapshot.live_cell?.di
                    ?.DI_002_part_present
                    ? "ON"
                    : "OFF"}
                </strong>
              </div>
            </div>
          </article>

          <article className="compact-card">
            <div className="compact-card-head">
              <h2>Axis & Servo</h2>
              <span>ZDT Axis/Servo</span>
            </div>

            <div className="compact-evidence-head">
              <div className="compact-alert-box">
                <span>Highest load</span>
                <strong>
                  {highestAxis
                    ? `J${highestAxis.axis} · ${highestAxis.axis_load_pct}%`
                    : "—"}
                </strong>
              </div>

              <div className="compact-alert-box">
                <span>Servo errors</span>
                <strong>{totalServoErrors}</strong>
              </div>
            </div>

            <div className="compact-axis-list">
              {axes.map((axis) => (
                <div
                  className="compact-axis-row"
                  key={axis.axis}
                >
                  <strong>J{axis.axis}</strong>

                  <div className="compact-axis-track">
                    <span
                      className={`compact-axis-fill compact-${tone(
                        axis.servo_indicator
                      )}`}
                      style={{
                        width: `${Math.min(
                          Number(axis.axis_load_pct || 0),
                          100
                        )}%`,
                      }}
                    />
                  </div>

                  <span>
                    {axis.axis_load_pct}%
                  </span>
                </div>
              ))}
            </div>
          </article>

          <article className="compact-card">
            <div className="compact-card-head">
              <h2>Alarms & AI Insights</h2>
              <span>Cross-check evidence</span>
            </div>

            <div className="compact-evidence-head">
              <div className="compact-alert-box">
                <span>Active alarm</span>
                <strong>
                  {activeAlarms[0]?.alarm_id || "None"}
                </strong>
              </div>

              <div className="compact-alert-box">
                <span>Maintenance due</span>
                <strong>{maintenanceDue.length}</strong>
              </div>
            </div>

            <div className="compact-insights">
              {selectedInsights.length ? (
                selectedInsights.slice(0, 3).map((insight) => (
                  <div
                    className="compact-insight"
                    key={insight.insight_id}
                  >
                    <div className="compact-insight-top">
                      <span>
                        {String(insight.category || "INSIGHT")
                          .replaceAll("_", " ")}
                      </span>

                      <Dot value={insight.severity} />
                    </div>

                    <strong>{insight.title}</strong>

                    <p className="compact-action">
                      <b>Action:</b>{" "}
                      {insight.recommended_action ||
                        insight.recommendation ||
                        "Continue monitoring."}
                    </p>
                  </div>
                ))
              ) : (
                <div className="compact-list-row">
                  <span>No AI insight requires attention.</span>
                </div>
              )}
            </div>
          </article>
        </div>
      </section>

      <section className="compact-ai" id="ask-my-robot">
        <div className="compact-ai-label">
          <strong>AI Analytics · Ask My Robot</strong>
          <span>
            Cross-check every answer with the selected robot evidence above.
          </span>
        </div>

        <AskMyRobot
          snapshot={snapshot}
          selectedRobotId={selectedRobotId}
          robots={fleetRobots}
          alarms={selectedAlarms}
          maintenance={selectedMaintenance}
          insights={selectedInsights}
        />
      </section>
    </div>
  );
}

export default App;
