import AITag from "./AITag";
import InfoPopover from "./InfoPopover";
import "./FeaturedRobotIntelligence.css";
import "./FeaturedRobotLayout.css";
import SimulationAnalytics from "./SimulationAnalytics";
import ClientRegisterData from "./ClientRegisterData";

const fmt = (value, decimals = 1) => Number.isFinite(Number(value)) ? Number(value).toFixed(decimals) : "—";
const label = (value) => String(value || "—").replaceAll("_", " ");

function seriesStats(points, field, lowerIsBetter = false) {
  const values = points.map((point) => Number(point?.[field])).filter(Number.isFinite);
  if (!values.length) return { min: null, max: null, average: null, trend: "UNAVAILABLE" };
  const window = Math.max(2, Math.min(12, Math.floor(values.length / 2)));
  const early = values.slice(0, window).reduce((sum, value) => sum + value, 0) / window;
  const late = values.slice(-window).reduce((sum, value) => sum + value, 0) / window;
  const delta = late - early;
  const stable = Math.abs(delta) < 0.1;
  return {
    min: Math.min(...values), max: Math.max(...values), average: values.reduce((sum, value) => sum + value, 0) / values.length,
    trend: stable ? "STABLE" : lowerIsBetter ? (delta < 0 ? "IMPROVING" : "DEGRADING") : (delta > 0 ? "IMPROVING" : "DEGRADING"),
    direction: stable ? "STABLE" : delta > 0 ? "INCREASING LOAD" : "DECREASING LOAD",
  };
}

function Section({ className = "", title, meta, children }) {
  return <article className={`featured-intel-card ${className}`}><header><h2>{title}</h2>{meta && <span>{meta}</span>}</header>{children}</article>;
}

export default function FeaturedRobotIntelligence({ robot, snapshot, production, oee, availability, performance, quality, axes, power, maintenance, alarms, insights, history, activeIndex }) {
  const cycle = seriesStats(history, "cycle_time_s", true);
  const oeeHistory = seriesStats(history, "oee_pct");
  const powerHistory = seriesStats(history, "power_kw", true);
  const axisRows = axes.map((axis) => ({ ...axis, history: seriesStats(history, `axis${axis.axis}_load_pct`) }));
  const highestAxis = axisRows.reduce((best, axis) => !best || Number(axis.axis_load_pct) > Number(best.axis_load_pct) ? axis : best, null);
  const mostErrors = axisRows.reduce((best, axis) => !best || Number(axis.error_count) > Number(best.error_count) ? axis : best, null);
  const totalErrors = axisRows.reduce((sum, axis) => sum + Number(axis.error_count || 0), 0);
  const due = maintenance.find((item) => ["OVERDUE", "DUE_SOON"].includes(item.status)) || maintenance[0];
  const maintenanceAxis = Number(String(due?.title || due?.component || "").match(/Axis\s+(\d+)/i)?.[1]);
  const attentionAxis = axisRows.find((axis) => axis.axis === maintenanceAxis) || axisRows.find((axis) => axis.servo_indicator !== "NORMAL") || mostErrors || highestAxis;
  const active = alarms.filter((alarm) => alarm.status === "ACTIVE");
  const latestAlarm = [...alarms].sort((a, b) => String(b.started_at).localeCompare(String(a.started_at)))[0];
  const alarmInsight = insights.find((item) => item.category === "ALARM_PATTERN");
  const mainInsight = insights[0];
  const currentCycle = Number(production.actual_cycle_time_s);
  const targetCycle = Number(production.target_cycle_time_s);
  const deviationSeconds = Number.isFinite(currentCycle) && Number.isFinite(targetCycle) ? currentCycle - targetCycle : null;
  const deviationPct = deviationSeconds == null || !targetCycle ? null : (deviationSeconds / targetCycle) * 100;
  const status = snapshot.robot_status?.mechanical_status || snapshot.mechanical_status || "—";

  return <div className="featured-intelligence-grid">
    <Section className="featured-operation" title="Operation Profile" meta="FEATURED ROBOT · DEEP ANALYTICS">
      <div className="featured-profile-list">
        <div><span>Robot ID</span><strong>{robot.id}</strong></div><div><span>Model</span><strong>{robot.model}</strong></div>
        <div><span>Application</span><strong>{robot.application || "Not specified"}</strong></div><div><span>Zone / Exhibition Area</span><strong>{robot.zone || robot.location || "Not specified"}</strong></div>
        <div><span>Controller IP</span><strong>{robot.ipAddress || "Not available"}</strong></div><div><span>Connection status</span><strong>Registry address only · not live connected</strong></div>
        <div><span>Current state</span><strong>{snapshot.live_cell?.state || snapshot.state}</strong></div><div><span>Health status</span><strong>{status}</strong></div>
      </div>
    </Section>

    <ClientRegisterData robot={robot} />

    <Section className="featured-performance" title="Performance Intelligence" meta={`${history.length}-point history`}>
      <div className="featured-stat-grid">
        <div><span>Current OEE</span><strong>{fmt(oee)}%</strong></div><div><span>Availability</span><strong>{fmt(availability)}%</strong></div>
        <div><span>Performance</span><strong>{fmt(performance)}%</strong></div><div><span>Quality</span><strong>{fmt(quality)}%</strong></div>
        <div><span>Target cycle</span><strong>{fmt(targetCycle)} s</strong></div><div><span>Current cycle</span><strong>{fmt(currentCycle)} s</strong></div>
        <div><span>Cycle deviation</span><strong>{deviationSeconds == null ? "—" : `${deviationSeconds >= 0 ? "+" : ""}${fmt(deviationSeconds)} s`}</strong></div>
        <div><span>Cycle deviation</span><strong>{deviationPct == null ? "—" : `${deviationPct >= 0 ? "+" : ""}${fmt(deviationPct)}%`}</strong></div>
        <div><span>Historical average</span><strong>{fmt(cycle.average, 2)} s</strong></div><div><span>Historical min</span><strong>{fmt(cycle.min)} s</strong></div>
        <div><span>Historical max</span><strong>{fmt(cycle.max)} s</strong></div><div><span>Recent cycle trend</span><strong>{cycle.trend}</strong></div>
      </div>
    </Section>

    <Section className="featured-axis" title="Axis & Servo Deep View" meta={`Highest J${highestAxis?.axis || "—"} · ${fmt(highestAxis?.axis_load_pct)}%`}>
      <div className="featured-axis-summary"><span>Most servo errors <b>J{mostErrors?.axis || "—"} · {mostErrors?.error_count ?? "—"}</b></span><span>Attention axis <b>J{attentionAxis?.axis || "—"}</b></span></div>
      <div className="featured-axis-table">
        {axisRows.map((axis) => <div className="featured-axis-row" key={axis.axis}>
          <b>J{axis.axis}</b><div className="featured-axis-bar"><i style={{ width: `${Math.min(Number(axis.axis_load_pct || 0), 100)}%` }} /></div>
          <span>{fmt(axis.axis_load_pct)}%</span><small>Hist max {fmt(axis.history.max)}% · {axis.error_count} error(s) · {axis.servo_indicator} · {axis.history.direction}</small>
        </div>)}
      </div>
    </Section>

    <Section className="featured-risk" title={<>Maintenance & Risk <InfoPopover label="How maintenance and risk are assessed" title="How this is assessed"><p>Maintenance and risk are assessed using scheduled maintenance status, remaining service hours, alarm severity, mechanical condition, servo errors, axis-load evidence, and recent performance trends.</p><p>This is an evidence-based attention assessment, not a predictive failure probability.</p></InfoPopover></>} meta="Evidence-based attention">
      <div className="featured-list">
        <div><span>Maintenance item</span><strong>{due?.title || "No scheduled item"}</strong></div><div><span>Status / remaining</span><strong>{label(due?.status)} · {due?.remaining_hours ?? "—"} h</strong></div>
        <div><span>Priority</span><strong>{due?.priority || "LOW"}</strong></div><div><span>Mechanical status</span><strong>{status}</strong></div>
        <div><span>Current alarm severity</span><strong>{active[0]?.severity || "NONE"}</strong></div><div><span>Servo errors</span><strong>{totalErrors}</strong></div>
        <div><span>Highest axis load</span><strong>J{highestAxis?.axis || "—"} · {fmt(highestAxis?.axis_load_pct)}%</strong></div><div><span>Inspection priority</span><strong>{due?.recommended_action || "Continue scheduled monitoring."}</strong></div>
      </div>
    </Section>

    <Section className="featured-alarm" title="Alarm Intelligence" meta="Associated observations">
      <div className="featured-stat-grid compact-six"><div><span>Active count</span><strong>{active.length}</strong></div><div><span>Latest ID</span><strong>{latestAlarm?.alarm_id || "None"}</strong></div><div><span>Severity</span><strong>{latestAlarm?.severity || "NONE"}</strong></div><div><span>Recent history</span><strong>{alarms.length} event(s)</strong></div></div>
      <div className="featured-callout"><b>{latestAlarm?.message || "No alarm message"}</b><span>{latestAlarm?.started_at ? new Date(latestAlarm.started_at).toLocaleString("en-IN") : "No start time"}</span><p>Associated observations: {alarmInsight?.evidence || `${attentionAxis ? `J${attentionAxis.axis} is the current attention axis` : "axis evidence is normal"}; recent cycle trend is ${cycle.trend.toLowerCase()}.`} This does not establish root cause.</p></div>
    </Section>

    <Section className="featured-energy" title={<>Energy & Load <InfoPopover label="How energy efficiency is estimated" title="Energy efficiency"><p>Energy efficiency is estimated from available power/energy telemetry and operating behavior. It is intended for comparative analytics and optimization support, not as a FANUC-certified energy metric.</p></InfoPopover></>} meta={`Power · ${powerHistory.trend}`}>
      <div className="featured-stat-grid"><div><span>Current power</span><strong>{fmt(power.instantaneous_kw, 2)} kW</strong></div><div><span>Historical average</span><strong>{fmt(powerHistory.average, 2)} kW</strong></div><div><span>Historical max</span><strong>{fmt(powerHistory.max, 2)} kW</strong></div><div><span>Total energy</span><strong>{fmt(power.kwh_total)} kWh</strong></div><div><span>Run energy</span><strong>{fmt(power.kwh_run)} kWh</strong></div><div><span>Idle energy</span><strong>{fmt(power.kwh_idle)} kWh</strong></div><div><span>Regeneration</span><strong>{fmt(power.kwh_regen)} kWh</strong></div><div><span>Power trend</span><strong>{powerHistory.trend}</strong></div></div>
    </Section>

    <Section className="featured-trends" title="Recent Trend Summary" meta="Latest supported history">
      <div className="featured-trend-strip"><div><span>Cycle</span><strong>{cycle.trend}</strong></div><div><span>OEE</span><strong>{oeeHistory.trend}</strong></div><div><span>Power</span><strong>{powerHistory.trend}</strong></div><div><span>Axis {attentionAxis?.axis || "—"}</span><strong>{attentionAxis?.history.direction || "—"}</strong></div><div><span>Alarm</span><strong>{active.length} ACTIVE · {latestAlarm?.severity || "NONE"}</strong></div><div><span>Maintenance</span><strong>{label(due?.status)}</strong></div></div>
    </Section>

    <SimulationAnalytics robotId={robot.id} points={history} activeIndex={activeIndex} featured />

    <Section className="featured-ai" title={<>AI / Analytics Insight <AITag /></>} meta="Grounded in dashboard evidence">
      <div className="featured-ai-grid"><div><span>Current condition</span><strong>{status} · {snapshot.live_cell?.state || snapshot.state}</strong></div><div><span>Main concern</span><strong>{mainInsight?.title || `J${attentionAxis?.axis || "—"} evidence`}</strong></div><div><span>Maintenance priority</span><strong>{due?.priority || "LOW"} · {label(due?.status)}</strong></div><div><span>Performance observation</span><strong>Cycle {cycle.trend.toLowerCase()} · OEE {oeeHistory.trend.toLowerCase()}</strong></div><div><span>Recommended first inspection</span><strong>{due?.recommended_action || mainInsight?.recommendation || "Continue monitoring available evidence."}</strong></div></div>
    </Section>
  </div>;
}
