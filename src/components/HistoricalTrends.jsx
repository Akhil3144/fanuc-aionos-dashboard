import { useEffect, useMemo, useState } from "react";
import { loadHistoricalTrends } from "../utils/analytics";
import "./HistoricalTrends.css";


function formatTime(timestamp) {
  if (!timestamp) return "—";

  return new Date(timestamp).toLocaleTimeString(
    "en-IN",
    {
      hour: "2-digit",
      minute: "2-digit",
    }
  );
}


function buildPath(data, field, width, height) {
  const valid = data
    .map((item, index) => ({
      index,
      value: item[field],
    }))
    .filter(
      (item) =>
        item.value !== null &&
        item.value !== undefined &&
        Number.isFinite(Number(item.value))
    );

  if (valid.length < 2) {
    return "";
  }

  const values = valid.map(
    (item) => Number(item.value)
  );

  let min = Math.min(...values);
  let max = Math.max(...values);

  if (min === max) {
    min -= 1;
    max += 1;
  }

  const paddingX = 4;
  const paddingY = 10;

  const usableWidth =
    width - paddingX * 2;

  const usableHeight =
    height - paddingY * 2;

  return valid
    .map((item, pointIndex) => {
      const x =
        paddingX +
        (item.index /
          Math.max(data.length - 1, 1)) *
          usableWidth;

      const normalized =
        (Number(item.value) - min) /
        (max - min);

      const y =
        paddingY +
        usableHeight -
        normalized * usableHeight;

      return `${
        pointIndex === 0 ? "M" : "L"
      } ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}


function TrendChart({
  title,
  unit,
  data,
  field,
  secondaryField,
  highlight,
}) {
  const width = 700;
  const height = 170;

  const primaryPath = useMemo(
    () =>
      buildPath(
        data,
        field,
        width,
        height
      ),
    [data, field]
  );

  const secondaryPath = useMemo(
    () =>
      secondaryField
        ? buildPath(
            data,
            secondaryField,
            width,
            height
          )
        : "",
    [data, secondaryField]
  );

  const values = data
    .map((item) => item[field])
    .filter(
      (value) =>
        value !== null &&
        value !== undefined
    )
    .map(Number);

  const latest =
    [...data]
      .reverse()
      .find(
        (item) =>
          item[field] !== null &&
          item[field] !== undefined
      )?.[field] ?? null;

  const minimum = values.length
    ? Math.min(...values)
    : null;

  const maximum = values.length
    ? Math.max(...values)
    : null;

  return (
    <div className="history-chart-card">
      <div className="history-chart-header">
        <div>
          <span>{title}</span>

          <strong>
            {latest !== null
              ? `${Number(latest).toFixed(2)} ${unit}`
              : "—"}
          </strong>
        </div>

        {highlight && (
          <small>{highlight}</small>
        )}
      </div>

      <div className="history-chart-wrapper">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
          className="history-svg"
        >
          <line
            x1="0"
            y1="42.5"
            x2={width}
            y2="42.5"
            className="history-grid-line"
          />

          <line
            x1="0"
            y1="85"
            x2={width}
            y2="85"
            className="history-grid-line"
          />

          <line
            x1="0"
            y1="127.5"
            x2={width}
            y2="127.5"
            className="history-grid-line"
          />

          {secondaryPath && (
            <path
              d={secondaryPath}
              className="history-line-secondary"
              fill="none"
              vectorEffect="non-scaling-stroke"
            />
          )}

          {primaryPath && (
            <path
              d={primaryPath}
              className="history-line-primary"
              fill="none"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
      </div>

      <div className="history-chart-footer">
        <span>
          Min{" "}
          <strong>
            {minimum !== null
              ? minimum.toFixed(2)
              : "—"}
          </strong>
        </span>

        <span>
          Max{" "}
          <strong>
            {maximum !== null
              ? maximum.toFixed(2)
              : "—"}
          </strong>
        </span>
      </div>
    </div>
  );
}


export default function HistoricalTrends() {
  const [trendData, setTrendData] =
    useState(null);

  const [error, setError] =
    useState(null);

  useEffect(() => {
    let active = true;

    loadHistoricalTrends({
      hours: 24,
      bucketMinutes: 15,
    })
      .then((result) => {
        if (active) {
          setTrendData(result);
        }
      })
      .catch((err) => {
        console.error(
          "Historical analytics error:",
          err
        );

        if (active) {
          setError(err.message);
        }
      });

    return () => {
      active = false;
    };
  }, []);


  const summary = useMemo(() => {
    if (!trendData?.data?.length) {
      return null;
    }

    const data =
      trendData.data;

    const cycles =
      data.reduce(
        (sum, item) =>
          sum +
          Number(
            item.cycles_completed || 0
          ),
        0
      );

    const faultMinutes =
      data.reduce(
        (sum, item) =>
          sum +
          Number(
            item.faulted_minutes || 0
          ),
        0
      );

    const staleMinutes =
      data.reduce(
        (sum, item) =>
          sum +
          Number(
            item.stale_minutes || 0
          ),
        0
      );

    const alarmBuckets =
      data.filter(
        (item) =>
          Number(
            item.maximum_active_alarms
          ) > 0
      ).length;

    return {
      cycles,
      faultMinutes,
      staleMinutes,
      alarmBuckets,
    };
  }, [trendData]);


  if (error) {
    return (
      <article className="panel historical-panel">
        <div className="historical-error">
          <strong>
            Historical analytics unavailable
          </strong>

          <span>{error}</span>
        </div>
      </article>
    );
  }


  if (!trendData || !summary) {
    return (
      <article className="panel historical-panel">
        <div className="historical-loading">
          Loading 24-hour analytics…
        </div>
      </article>
    );
  }


  const data =
    trendData.data;

  return (
    <article className="panel historical-panel">
      <div className="historical-header">
        <div>
          <span className="panel-eyebrow">
            Historical Analytics
          </span>

          <h2>
            24h Performance Trends
          </h2>

          <p>
            Production, Axis 4 condition and
            energy behaviour aggregated into
            15-minute intervals.
          </p>
        </div>

        <span className="source-tag">
          AIonOS Analytics
        </span>
      </div>


      <div className="historical-summary">
        <div>
          <span>Trend points</span>
          <strong>
            {trendData.points}
          </strong>
        </div>

        <div>
          <span>Cycles</span>
          <strong>
            {summary.cycles}
          </strong>
        </div>

        <div>
          <span>Fault minutes</span>
          <strong>
            {summary.faultMinutes}
          </strong>
        </div>

        <div>
          <span>Stale minutes</span>
          <strong>
            {summary.staleMinutes}
          </strong>
        </div>

        <div>
          <span>Alarm intervals</span>
          <strong>
            {summary.alarmBuckets}
          </strong>
        </div>
      </div>


      <div className="historical-chart-grid">
        <TrendChart
          title="Cycle Time"
          unit="s"
          data={data}
          field="average_cycle_time_s"
          highlight="Target 45 s"
        />

        <TrendChart
          title="Axis 4 Load"
          unit="%"
          data={data}
          field="average_axis_4_load_pct"
          secondaryField="maximum_axis_4_load_pct"
          highlight="Average + peak"
        />

        <TrendChart
          title="Robot Power"
          unit="kW"
          data={data}
          field="average_power_kw"
          secondaryField="peak_power_kw"
          highlight="Average + peak"
        />
      </div>


      <div className="historical-range">
        <span>
          {formatTime(
            trendData.window.start_time
          )}
        </span>

        <div></div>

        <span>
          {formatTime(
            trendData.window.end_time
          )}
        </span>
      </div>
    </article>
  );
}