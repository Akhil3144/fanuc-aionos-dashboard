import { Link } from "react-router-dom";
import "./RobotCard.css";
import "./RobotCardEnhancements.css";
import { imageForRobot } from "../data/robotImages";

export default function RobotCard({ robot, metrics }) {
  const tone = metrics.state === "RUNNING" ? "success" : metrics.state === "ATTENTION" ? "danger" : "warning";
  const image = imageForRobot(robot);
  return (
    <Link className={`robot-card${robot.featured ? " robot-card-featured" : ""}`} to={`/robot/${robot.id}`}>
      <div className="robot-card-head">
        <span>#{String(robot.serialNo).padStart(2, "0")} · {robot.id}</span>
        {robot.featured && <b>Featured</b>}
      </div>
      <div className="robot-card-image"><img src={image.src} alt={`${robot.model} ${image.family} family illustration`} loading="lazy" onError={(event) => { event.currentTarget.onerror = null; event.currentTarget.src = image.fallback; }} /></div>
      <h2>{robot.model}</h2>
      <p>{robot.application || "Application not specified"}</p>
      <div className="robot-card-registry"><span>{robot.zone || robot.location}</span><strong>{robot.ipAddress || "IP not set"}</strong></div>
      <div className="robot-card-sim">
        <div><span className={`robot-state robot-state-${tone}`}><i />{metrics.state}</span><small>Simulator</small></div>
        <div><span>OEE</span><strong>{metrics.oeePct}%</strong></div>
        <div><span>Cycle</span><strong>{metrics.cycleTimeSeconds}s</strong></div>
        <div><span>Alarms</span><strong>{metrics.activeAlarms}</strong></div>
      </div>
      {robot.featured && <div className="robot-card-intelligence" aria-label="Featured intelligence">
        <span><small>Power</small><strong>{metrics.powerKw == null ? "—" : `${Number(metrics.powerKw).toFixed(2)} kW`}</strong></span>
        <span><small>Highest axis</small><strong>{metrics.highestAxis ? `J${metrics.highestAxis.axis} · ${metrics.highestAxis.axis_load_pct}%` : "—"}</strong></span>
        <span><small>Mechanical</small><strong>{metrics.mechanicalStatus}</strong></span>
        <span><small>Servo errors</small><strong>{metrics.servoErrors ?? "—"}</strong></span>
      </div>}
    </Link>
  );
}
