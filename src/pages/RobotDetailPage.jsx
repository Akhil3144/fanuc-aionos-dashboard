import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "../App.css";
import AskMyRobot from "../components/AskMyRobot";
import RobotVideo from "../components/RobotVideo";
import SimulationAnalytics from "../components/SimulationAnalytics";
import { findRegistryRobot, robotRegistry } from "../data/robotRegistry";
import { simulatorSnapshotFor } from "../services/fleetSimulator";
import AITag from "../components/AITag";
import InfoPopover from "../components/InfoPopover";
import FeaturedRobotIntelligence from "../components/FeaturedRobotIntelligence";

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

function RobotDetailPage() {
  const { robotId } = useParams();
  const navigate = useNavigate();
  const [fleetRobots, setFleetRobots] = useState([]);
  const [selectedRobotId, setSelectedRobotId] = useState("");
  const [snapshot, setSnapshot] = useState(null);
  const [shiftSummary, setShiftSummary] = useState([]);
  const [allAlarms, setAllAlarms] = useState([]);
  const [allMaintenance, setAllMaintenance] = useState([]);
  const [allInsights, setAllInsights] = useState([]);
  const [simulationPoints, setSimulationPoints] = useState({});
  const [simulationIndex, setSimulationIndex] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    const legacy = !robotId;
    const base = legacy ? "/data_v3" : "/data_openhouse";
    const selectedId = findRegistryRobot(robotId)?.id || robotRegistry[0].id;
    Promise.all(legacy ? [
      loadJson(`${base}/fleet_latest_snapshot.json`),
      loadJson(`${base}/production_shift_summary.json`),
      loadJson(`${base}/alarms.json`),
      loadJson(`${base}/maintenance.json`),
      loadJson(`${base}/derived_insights.json`),
      loadJson(`${base}/simulation_10_points.json`),
    ] : [
      loadJson(`${base}/robot_current.json`),
      loadJson(`${base}/production.json`),
      loadJson(`${base}/alarms.json`),
      loadJson(`${base}/maintenance.json`),
      loadJson(`${base}/insights.json`),
      loadJson(`${base}/history/${selectedId}.json`),
    ])
      .then(
        ([
          fleetData,
          shiftData,
          alarmData,
          maintenanceData,
          insightData,
          simulationData,
        ]) => {
          const robots = Array.isArray(fleetData) ? fleetData : Array.isArray(fleetData?.robots) ? fleetData.robots : [];

          if (!robots.length) {
            throw new Error("No robot simulator data was found.");
          }

          const stored = localStorage.getItem("fanucSelectedRegistryRobotId");
          const initialRegistryRobot = robotId ? findRegistryRobot(robotId) : (findRegistryRobot(stored) || robotRegistry[0]);
          if (!initialRegistryRobot) throw new Error(`Robot ${robotId} was not found in the Open House registry.`);
          const initialSnapshot = legacy
            ? simulatorSnapshotFor(initialRegistryRobot, robots) || robots[0]
            : robots.find((item) => item.robot_id === initialRegistryRobot.id);
          if (!initialSnapshot) throw new Error(`Robot ${initialRegistryRobot.id} has no Open House operational data.`);

          setFleetRobots(robots);
          setSelectedRobotId(initialRegistryRobot.id);
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

          setSimulationPoints(legacy
            ? (simulationData && typeof simulationData === "object" ? simulationData : {})
            : { [initialRegistryRobot.id]: Array.isArray(simulationData) ? simulationData : [] });
        }
      )
      .catch((err) => {
        console.error(err);
        setError(err.message);
      });
  }, [robotId]);

  useEffect(() => {
    if (!fleetRobots.length || !robotId) return;

    const registryRobot = findRegistryRobot(robotId);
    const next = fleetRobots.find((item) => item.robot_id === robotId);

    if (registryRobot && next) {
      setSelectedRobotId(robotId);
      setSnapshot(next);
      localStorage.setItem("fanucSelectedRegistryRobotId", robotId);
    }
  }, [fleetRobots, robotId]);

  const selectedSimulationPoints = useMemo(() => {
    const points = simulationPoints?.[snapshot?.robot_id];

    return Array.isArray(points) ? points : [];
  }, [simulationPoints, snapshot?.robot_id]);

  useEffect(() => {
    setSimulationIndex(0);

    if (selectedSimulationPoints.length <= 1) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setSimulationIndex((current) =>
        (current + 1) % selectedSimulationPoints.length
      );
    }, 2000);

    return () => window.clearInterval(timer);
  }, [selectedRobotId, selectedSimulationPoints.length]);

  const selectRobot = (event) => {
    const id = event.target.value;
    navigate(`/robot/${encodeURIComponent(id)}`);
  };

  const selectedAlarms = useMemo(() => {
    if (!snapshot?.robot_id) return [];

    const activeIds =
      snapshot?.alarms?.active_alarm_ids || [];

    return allAlarms
      .filter(
        (alarm) => alarm.robot_id === snapshot.robot_id
      )
      .map((alarm) => ({
        ...alarm,
        status: activeIds.includes(alarm.alarm_id)
          ? "ACTIVE"
          : alarm.status === "ACTIVE"
            ? "CLEARED"
            : alarm.status,
      }));
  }, [allAlarms, snapshot]);

  const selectedMaintenance = useMemo(
    () =>
      allMaintenance.filter(
        (item) => item.robot_id === snapshot?.robot_id
      ),
    [allMaintenance, snapshot?.robot_id]
  );

  const selectedInsights = useMemo(
    () =>
      allInsights.filter(
        (item) =>
          item.robot_id === snapshot?.robot_id &&
          item.category !== "CONNECTIVITY"
      ),
    [allInsights, snapshot?.robot_id]
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
  const registryRobot = findRegistryRobot(selectedRobotId) || robotRegistry[0];
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
      item.category === "ANOMALY" ||
      ["CYCLE_DEGRADATION", "AXIS_LOAD_TREND", "POWER_ANOMALY", "MAINTENANCE_DUE", "ALARM_PATTERN", "HEALTH_ATTENTION"].includes(item.category)
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

  const historyStats = (() => {
    const values = (field) => selectedSimulationPoints.map((point) => Number(point?.[field])).filter(Number.isFinite);
    const summarize = (field) => {
      const series = values(field);
      if (!series.length) return { min: null, max: null, average: null, latest: null, trend: "Unavailable" };
      const window = Math.max(2, Math.min(12, Math.floor(series.length / 2)));
      const early = series.slice(0, window).reduce((sum, value) => sum + value, 0) / window;
      const late = series.slice(-window).reduce((sum, value) => sum + value, 0) / window;
      const delta = late - early;
      return {
        min: Math.min(...series), max: Math.max(...series),
        average: series.reduce((sum, value) => sum + value, 0) / series.length,
        latest: series.at(-1), trend: Math.abs(delta) < 0.1 ? "Stable" : delta > 0 ? "Increasing" : "Decreasing",
      };
    };
    return { cycle: summarize("cycle_time_s"), power: summarize("power_kw"), oee: summarize("oee_pct") };
  })();

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

        .compact-back { display:inline-block; margin-bottom:8px; color:#75cbd0; font-size:9px; font-weight:750; letter-spacing:.12em; text-decoration:none; text-transform:uppercase; }
        .featured-flags { display:flex; gap:7px; margin:8px 0 0; }
        .featured-flags b { padding:5px 8px; border:1px solid rgba(245,190,72,.35); border-radius:999px; color:#f4c76b; background:rgba(245,190,72,.08); font-size:8px; letter-spacing:.12em; }
        .registry-detail-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:8px; padding:9px 11px; border:1px solid rgba(93,195,201,.18); border-radius:10px; background:rgba(27,57,67,.18); }
        .registry-detail-strip span { display:block; margin-bottom:3px; opacity:.5; font-size:8px; letter-spacing:.1em; text-transform:uppercase; }
        .registry-detail-strip strong { display:block; font-size:11px; }

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
          grid-template-columns: repeat(12, minmax(0, 1fr));
          gap: 16px;
          align-items: stretch;
        }

        .normal-evidence-grid > :nth-child(1), .normal-evidence-grid > :nth-child(2),
        .normal-evidence-grid > :nth-child(5), .normal-evidence-grid > :nth-child(6) { grid-column: span 6; }
        .normal-evidence-grid > :nth-child(3) { grid-column: span 7; }
        .normal-evidence-grid > :nth-child(4) { grid-column: span 5; }
        .featured-evidence-grid > :nth-child(1) { grid-column: span 8; }
        .featured-evidence-grid > :nth-child(2) { grid-column: span 4; }
        .featured-evidence-grid > :nth-child(3) { grid-column: span 7; }
        .featured-evidence-grid > :nth-child(4) { grid-column: span 5; }
        .featured-evidence-grid > :nth-child(5), .featured-evidence-grid > :nth-child(6) {
          grid-column: span 6; width: 100%; min-width: 0; box-sizing: border-box;
        }
        .featured-evidence-grid > :nth-child(6) .compact-stat-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .featured-summary-grid > * { grid-column: 1 / -1; }

        .compact-card {
          border: 1px solid rgba(255,255,255,.10);
          border-radius: 12px;
          padding: 10px 11px;
          background: rgba(255,255,255,.018);
          min-width: 0;
          min-height: 224px;
          height: auto;
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

        .compact-list-row small { display:block; margin-top:2px; opacity:.62; }

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

        .compact-axis-row small { grid-column:2 / 4; opacity:.5; }

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

        @media (max-width: 1200px) {
          .compact-kpis {
            grid-template-columns: repeat(3, 1fr);
          }

          .compact-evidence-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .compact-evidence-grid > * { grid-column: span 1 !important; }

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

          .registry-detail-strip { grid-template-columns: 1fr 1fr; }
        }
      `}</style>

      <section className="compact-top">
        <header className="compact-header">
          <div>
            {robotId && <a className="compact-back" href="/fleet">← BACK TO ROBOT FLEET</a>}
            <div className="compact-brand-kicker">
              FANUC × AIonOS
            </div>

            <h1>{registryRobot.model}</h1>

            <p>
              {registryRobot.application || "Application not specified"} · Open House 2026 registry
            </p>
            {registryRobot.featured && <div className="featured-flags"><b>FEATURED ROBOT</b><b>DEEP ANALYTICS</b></div>}
          </div>

          <div className="compact-controls">
            {!robotId && <label className="compact-select-wrap">
              <span>Robot</span>

              <select
                value={selectedRobotId}
                onChange={selectRobot}
              >
                {robotRegistry.map((robot) => (
                  <option
                    key={robot.id}
                    value={robot.id}
                  >
                    #{robot.serialNo} — {robot.model}
                  </option>
                ))}
              </select>
            </label>}

            <span className="compact-chip">
              <Dot value="NORMAL" />
              SYSTEM READY
            </span>

            <span className="compact-chip">
              TELEMETRY · SIMULATOR
            </span>

            <span className="compact-chip">
              READ ONLY
            </span>
          </div>
        </header>

        {registryRobot.featured && <div className="compact-card-head"><h2>Operation Profile</h2><span>Registry configuration</span></div>}
        <div className="registry-detail-strip">
          <div><span>Registry ID</span><strong>{registryRobot.id} · Serial {registryRobot.serialNo}</strong></div>
          <div><span>Robot model</span><strong>{registryRobot.model}</strong></div>
          <div><span>Application</span><strong>{registryRobot.application || "Not specified"}</strong></div>
          <div><span>Controller IP</span><strong>{registryRobot.ipAddress || "Not available"}</strong></div>
          {registryRobot.featured && <div><span>Featured status</span><strong>FEATURED ROBOT · DEEP ANALYTICS</strong></div>}
        </div>

        <div className="compact-kpis">
          <MiniMetric
            label="Current State"
            value={snapshot.live_cell?.state || "—"}
            helper={snapshot.display_name}
          />

          <MiniMetric
            label="OEE"
            value={`${oee}%`}
            helper={`Shift ${snapshot.shift}`}
          />

          <MiniMetric
            label="Cycle Time"
            value={production.actual_cycle_time_s != null ? `${production.actual_cycle_time_s}s` : "—"}
            helper={`Target ${production.target_cycle_time_s ?? "—"}s`}
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
            label="Health Status"
            value={health.mechanical_status || "—"}
            helper={`${predictiveAlerts} insight(s) · ${maintenanceDue.length} due`}
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


        {registryRobot.featured ? <FeaturedRobotIntelligence
          robot={registryRobot}
          snapshot={snapshot}
          production={production}
          oee={oee}
          availability={availability}
          performance={performance}
          quality={quality}
          axes={axes}
          power={power}
          maintenance={selectedMaintenance}
          alarms={selectedAlarms}
          insights={selectedInsights}
          history={selectedSimulationPoints}
          activeIndex={simulationIndex}
        /> : <div className="compact-evidence-grid normal-evidence-grid">
          <article className="compact-card">
            <div className="compact-card-head">
              <h2>Production</h2>
              <span>Production Metrics</span>
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
              <span>Robot Status</span>
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
              <h2>{registryRobot.featured ? "Axis / Servo Deep Analysis" : "Axis & Servo"}</h2>
              <span>Axis / Servo</span>
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
                  {registryRobot.featured && <small>{axis.error_count} errors · {axis.servo_indicator} · {Number(axis.odometer).toLocaleString("en-IN")} odo</small>}
                </div>
              ))}
            </div>
          </article>

          <article className="compact-card">
            <div className="compact-card-head">
              <h2>{registryRobot.featured ? "Alarm Intelligence" : "Alarms & Insights"}</h2>
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
              {selectedAlarms.slice(0, 2).map((alarm) => (
                <div className="compact-insight" key={alarm.alarm_id}>
                  <div className="compact-insight-top"><span>{alarm.status} · {alarm.severity}</span><Dot value={alarm.severity} /></div>
                  <strong>{alarm.alarm_id}</strong><p className="compact-action">{alarm.message}</p>
                </div>
              ))}
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
                        {" "}<AITag />
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

          <article className="compact-card">
            <div className="compact-card-head"><h2>{registryRobot.featured ? "Maintenance & Risk" : "Maintenance"}<InfoPopover label="How maintenance and risk are assessed" title="Maintenance, reliability & risk"><p><b>Maintenance:</b> shown directly from scheduled service records using remaining hours and OK, due-soon or overdue status. Alarm and servo evidence is shown alongside it but does not alter the schedule.</p><p><b>Reliability:</b> the fleet value is simulator availability; robot condition uses current working, process and mechanical status.</p><p><b>Risk / attention:</b> a heuristic ranking of overdue maintenance, alarm severity/count, mechanical status, OEE, axis load and servo errors. It is not a predicted failure probability.</p></InfoPopover></h2><span>Service condition</span></div>
            <div className="compact-list">
              {selectedMaintenance.map((item) => (
                <div className="compact-list-row" key={item.maintenance_id}>
                  <span>{item.component}<small>{item.description}</small></span>
                  <strong><Dot value={item.status} />{String(item.status).replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())} · {String(item.priority).toLowerCase().replace(/^./, (c) => c.toUpperCase())} Priority · {item.remaining_hours} h remaining</strong>
                </div>
              ))}
              {registryRobot.featured && selectedMaintenance[0] && <div className="compact-insight"><strong>Recommended inspection priority</strong><p className="compact-action">{selectedMaintenance[0].recommended_action}</p></div>}
            </div>
          </article>

          <article className="compact-card">
            <div className="compact-card-head"><h2>{registryRobot.featured ? "Energy & Load" : "Energy"}<InfoPopover label="How energy efficiency is estimated" title="Energy efficiency"><p>These values are simulator-derived power and accumulated energy telemetry. The trend compares the early and late portions of the available history window.</p><p>They support comparison, optimization and maintenance investigation. This is an analytical estimate based on available dashboard telemetry and is not a direct FANUC/ZDT energy certification.</p></InfoPopover></h2><span>Power trend · {historyStats.power.trend}</span></div>
            <div className="compact-stat-grid">
              <div className="compact-stat"><span>Current</span><strong>{Number(power.instantaneous_kw).toFixed(2)} kW</strong></div>
              <div className="compact-stat"><span>Total</span><strong>{Number(power.kwh_total).toFixed(1)} kWh</strong></div>
              <div className="compact-stat"><span>Running</span><strong>{Number(power.kwh_run).toFixed(1)} kWh</strong></div>
              <div className="compact-stat"><span>Idle</span><strong>{Number(power.kwh_idle).toFixed(1)} kWh</strong></div>
              <div className="compact-stat"><span>Fault</span><strong>{Number(power.kwh_fault).toFixed(1)} kWh</strong></div>
              <div className="compact-stat"><span>Regeneration</span><strong>{Number(power.kwh_regen).toFixed(1)} kWh</strong></div>
            </div>
          </article>
        </div>}
      </section>

      {!robotId && (
        <RobotVideo
          robotId={snapshot.robot_id}
          robot={snapshot}
        />
      )}

        {!registryRobot.featured && <SimulationAnalytics
          robotId={snapshot.robot_id}
          points={selectedSimulationPoints}
          activeIndex={simulationIndex}
          featured={registryRobot.featured}
        />}

        <section className="compact-ai" id="ask-my-robot">
        <div className="compact-ai-label">
          <strong>AI Analytics · Ask My Robot <AITag /></strong>
          <span>
            Cross-check every answer with the selected robot evidence above.
          </span>
        </div>

        <AskMyRobot
          robotId={robotId}
          scope="ROBOT"
          snapshot={snapshot}
          selectedRobotId={selectedRobotId}
          robots={fleetRobots}
          registry={robotRegistry}
          registryRobot={registryRobot}
          alarms={selectedAlarms}
          maintenance={selectedMaintenance}
          insights={selectedInsights}
        />
      </section>
    </div>
  );
}

export default RobotDetailPage;
