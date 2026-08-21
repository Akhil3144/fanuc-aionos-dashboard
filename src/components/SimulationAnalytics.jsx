
import "./SimulationAnalytics.css";

function makeSeries(points, field) {
  const valid = points
    .map((point, index) => ({
      index,
      value: Number(point?.[field]),
    }))
    .filter((point) => Number.isFinite(point.value));

  if (!valid.length) {
    return { path: "", dots: [], min: null, max: null };
  }

  const values = valid.map((item) => item.value);

  const realMin = Math.min(...values);
  const realMax = Math.max(...values);

  let min = realMin;
  let max = realMax;

  if (min === max) {
    min -= 1;
    max += 1;
  }

  const width = 400;
  const height = 105;
  const px = 10;
  const py = 10;

  const dots = valid.map((item) => {
    const x =
      px +
      (item.index / Math.max(points.length - 1, 1)) *
        (width - px * 2);

    const y =
      py +
      (height - py * 2) -
      ((item.value - min) / (max - min)) *
        (height - py * 2);

    return { ...item, x, y };
  });

  const path = dots
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${point.x.toFixed(
          2
        )} ${point.y.toFixed(2)}`
    )
    .join(" ");

  return {
    path,
    dots,
    min: realMin,
    max: realMax,
  };
}

function Graph({
  title,
  field,
  unit,
  points,
  activeIndex,
  decimals,
}) {
  const series = makeSeries(points, field);

  const raw = Number(points?.[activeIndex]?.[field]);
  const current = Number.isFinite(raw) ? raw : null;

  return (
    <div className="sim-graph-card">
      <div className="sim-graph-header">
        <div>
          <span>{title}</span>
          <strong>
            {current !== null
              ? `${current.toFixed(decimals)} ${unit}`
              : "—"}
          </strong>
        </div>

        
      </div>

      <svg
        viewBox="0 0 400 105"
        preserveAspectRatio="none"
        className="sim-graph-svg"
      >
        <line x1="0" x2="400" y1="26" y2="26" className="sim-grid-line" />
        <line x1="0" x2="400" y1="52" y2="52" className="sim-grid-line" />
        <line x1="0" x2="400" y1="78" y2="78" className="sim-grid-line" />

        {series.path && (
          <path
            d={series.path}
            className="sim-graph-line"
            fill="none"
            vectorEffect="non-scaling-stroke"
          />
        )}

        {series.dots.map((dot) => (
          <circle
            key={`${field}-${dot.index}`}
            cx={dot.x}
            cy={dot.y}
            r={dot.index === activeIndex ? 4 : 2.6}
            className={
              dot.index === activeIndex
                ? "sim-graph-dot active"
                : "sim-graph-dot"
            }
          />
        ))}
      </svg>

      <div className="sim-graph-footer">
        <span>
          Min{" "}
          <strong>
            {series.min !== null
              ? series.min.toFixed(decimals)
              : "—"}
          </strong>
        </span>

        <span>
          Max{" "}
          <strong>
            {series.max !== null
              ? series.max.toFixed(decimals)
              : "—"}
          </strong>
        </span>
      </div>
    </div>
  );
}

export default function SimulationAnalytics({
  robotId,
  points = [],
  activeIndex = 0,
  featured = false,
}) {
  const active = points?.[activeIndex];

  return (
    <section className="simulation-analytics-clean">
      <div className="simulation-clean-head">
        <div>
          <span>TELEMETRY · SIMULATOR</span>
          <h2>{featured ? "Historical Analytics" : "Telemetry / Historical Trends"}</h2>
          <p>
            {featured ? "Cycle, OEE, J1–J6, power, state and alarm evidence." : "Cycle time, Axis 4 load and power trends."}
          </p>
        </div>

        <div className="simulation-clean-status">
          <strong>{robotId}</strong>

          

          <b>{active?.state || "—"}</b>
        </div>
      </div>

      <div className="simulation-graph-grid">
        <Graph
          title="Cycle Time"
          field="cycle_time_s"
          unit="s"
          points={points}
          activeIndex={activeIndex}
          decimals={2}
        />

        <Graph
          title="Axis 4 Load"
          field="axis4_load_pct"
          unit="%"
          points={points}
          activeIndex={activeIndex}
          decimals={1}
        />

        <Graph
          title="Power"
          field="power_kw"
          unit="kW"
          points={points}
          activeIndex={activeIndex}
          decimals={2}
        />

        {featured && <Graph title="OEE" field="oee_pct" unit="%" points={points} activeIndex={activeIndex} decimals={1} />}

        {featured && [1, 2, 3, 4, 5, 6].map((axis) => (
          <Graph key={axis} title={`Axis J${axis} Load`} field={`axis${axis}_load_pct`} unit="%" points={points} activeIndex={activeIndex} decimals={1} />
        ))}
      </div>

      <div className={`simulation-sequence${featured ? " simulation-timeline" : ""}`} aria-label="State and alarm timeline">
        {points.map((point, index) => (
          <span
            key={`${point.timestamp}-${index}`}
            title={`${point.state} · ${point.active_alarm_count || 0} alarm(s)`}
            className={`${index === activeIndex ? "active " : ""}${point.state === "FAULTED" ? "faulted " : ""}${point.active_alarm_count ? "alarm" : ""}`.trim()}
          />
        ))}
      </div>
    </section>
  );
}
