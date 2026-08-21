import "./FleetExecutiveCards.css";

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
      accent: "green", eyebrow: "Fleet reliability", value: `${summary.reliabilityPct}%`, unit: "reliability",
      description: "Overall fleet reliability and operational condition.",
      metrics: [["Healthy robots", summary.healthy, "success"], ["Attention robots", summary.attention, "warning"], ["Critical robots", summary.critical, "danger"]],
    },
    {
      accent: "amber", eyebrow: "Maintenance & risk", value: summary.activeAlarms, unit: "active alarms",
      description: "Current operational risk across the exhibition fleet.",
      metrics: [["Critical alarms", summary.criticalAlarms, "danger"], ["Maintenance due", summary.maintenanceDue, "warning"], ["Require attention", summary.attentionRobots, "warning"]],
    },
  ];

  return (
    <div className="executive-cards">
      <div className="primary-card-grid">
        {primaryCards.map((card) => (
          <article className={`fleet-card fleet-card-${card.accent}`} key={card.eyebrow}>
            <div className="fleet-card-top"><p>{card.eyebrow}</p><i /></div>
            <div className="fleet-card-value"><strong>{card.value}</strong>{card.unit && <span>{card.unit}</span>}</div>
            <div className="fleet-card-metrics">{card.metrics.map(([label, value, tone]) => <Metric key={label} label={label} value={value} tone={tone} />)}</div>
            <p className="fleet-card-description">{card.description}</p>
          </article>
        ))}
      </div>
      <div className="secondary-card-grid">
        <article><span>Energy efficiency</span><strong>{summary.currentFleetPowerKw} <small>kW</small></strong><p>{summary.energyPerCycleKwh} kWh average per cycle</p></article>
        <article><span>Application coverage</span><strong>{summary.applicationTypes} <small>types</small></strong><p>{summary.featuredRobots} featured · Open House registry</p></article>
        <article><span>Fleet attention</span><strong className="tone-warning">{summary.attentionRobots} <small>robots</small></strong><p>Assets currently needing review</p></article>
      </div>
    </div>
  );
}

export default FleetExecutiveCards;
