import "./FleetExecutiveCards.css";
import InfoPopover from "./InfoPopover";

const number = new Intl.NumberFormat("en-US");

function Metric({ label, value, tone }) {
  return <div className="fleet-card-metric"><span>{label}</span><strong className={tone ? `tone-${tone}` : ""}>{value}</strong></div>;
}

function FleetExecutiveCards({ summary }) {
  const primaryCards = [
    {
      accent: "cyan", eyebrow: "Fleet utilization", value: `${summary.utilizationPct}%`,
      description: "How effectively the complete robot fleet is being used.",
      metrics: [["Running robots", summary.running, "success"], ["Ready / Idle", summary.readyIdle, "warning"], ["Total robots", summary.totalRobots]],
    },
    {
      accent: "blue", eyebrow: "Throughput", value: number.format(summary.throughput), unit: "cycles",
      description: "Overall production output across the fleet.",
      metrics: [["Avg. cycle performance", `${summary.averageCyclePerformancePct}%`], ["Target achievement", `${summary.targetAchievementPct}%`, "success"]],
    },
    {
      accent: "green", eyebrow: "Fleet reliability", value: `${summary.reliabilityPct}%`, unit: "availability",
      description: "Simulator fleet availability; a reliability indicator, not a predicted failure probability.", info: "reliability",
      metrics: [["Healthy robots", summary.healthy, "success"], ["Attention robots", summary.attention, "warning"], ["Critical robots", summary.critical, "danger"]],
    },
    {
      accent: "amber", eyebrow: "Maintenance & risk", value: summary.activeAlarms, unit: "active alarms",
      description: "Current evidence-based attention indicators across the exhibition fleet.", info: "risk",
      metrics: [["Critical alarms", summary.criticalAlarms, "danger"], ["Maintenance due", summary.maintenanceDue, "warning"], ["Require attention", summary.attentionRobots, "warning"]],
    },
  ];

  return (
    <div className="executive-cards">
      <div className="primary-card-grid">
        {primaryCards.map((card) => (
          <article className={`fleet-card fleet-card-${card.accent}`} key={card.eyebrow}>
            <div className="fleet-card-top"><p>{card.eyebrow}{card.info && <InfoPopover actionLabel="How assessed" label={`How ${card.eyebrow.toLowerCase()} is assessed`} title={card.info === "reliability" ? "How Fleet Reliability Is Assessed" : "How Maintenance & Risk Are Assessed"}>{card.info === "reliability" ? <><p>The displayed reliability percentage is the current simulator fleet availability percentage.</p><p>Supporting health evidence includes operating state, mechanical condition, alarms, servo errors, and recent operational stability. Healthy, attention, and critical counts come from current mechanical-status categories.</p><p>It is an operational indicator, not a predicted probability of failure.</p></> : <><p>The fleet summary uses active and critical alarms, scheduled maintenance state, remaining service hours, overdue or due-soon items, and current mechanical attention status.</p><p>Detailed attention prioritization also considers alarm severity, servo errors, high axis-load evidence, OEE, and degrading production trends where available.</p><p>Assets with stronger combinations of overdue maintenance, severe alarms, mechanical attention, servo errors, and abnormal operational trends receive higher attention priority. This does not predict root cause or failure probability.</p></>}</InfoPopover>}</p><i /></div>
            <div className="fleet-card-value"><strong>{card.value}</strong>{card.unit && <span>{card.unit}</span>}</div>
            <div className="fleet-card-metrics">{card.metrics.map(([label, value, tone]) => <Metric key={label} label={label} value={value} tone={tone} />)}</div>
            <p className="fleet-card-description">{card.description}</p>
          </article>
        ))}
      </div>
      <div className="secondary-card-grid">
        <article><span>Energy efficiency <InfoPopover actionLabel="How estimated" label="How energy efficiency is estimated" title="How Energy Efficiency Is Estimated"><p>Current fleet power is summed from simulator power telemetry. Energy per cycle is calculated from the available total fleet energy divided by completed cycles.</p><p>Available power and energy totals can be compared across operating behavior and history to identify high-energy periods, compare robots or applications, identify optimization opportunities, and support maintenance investigation.</p><p>This is an analytical estimate based on available dashboard telemetry, not a FANUC-certified energy metric.</p></InfoPopover></span><strong>{summary.currentFleetPowerKw} <small>kW</small></strong><p>{summary.energyPerCycleKwh} kWh average per cycle</p></article>
        <article><span>Application coverage</span><strong>{summary.applicationTypes} <small>types</small></strong><p>{summary.featuredRobots} featured · Open House registry</p></article>
        <article><span>Fleet attention</span><strong className="tone-warning">{summary.attentionRobots} <small>robots</small></strong><p>Assets currently needing review</p></article>
      </div>
    </div>
  );
}

export default FleetExecutiveCards;
