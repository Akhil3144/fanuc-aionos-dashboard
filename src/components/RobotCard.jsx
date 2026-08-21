import { Link } from "react-router-dom";
import "./RobotCard.css";

export default function RobotCard({ robot, metrics }) {
  const tone = metrics.state === "RUNNING" ? "success" : metrics.state === "ATTENTION" ? "danger" : "warning";
  return (
    <Link className={`robot-card${robot.featured ? " robot-card-featured" : ""}`} to={`/robot/${robot.id}`}>
      <div className="robot-card-head">
        <span>#{String(robot.serialNo).padStart(2, "0")} · {robot.id}</span>
        {robot.featured && <b>Featured</b>}
      </div>
      <h2>{robot.model}</h2>
      <p>{robot.application || "Application not specified"}</p>
      <div className="robot-card-registry"><span>Registry IP</span><strong>{robot.ipAddress || "Not available"}</strong></div>
      <div className="robot-card-sim">
        <div><span className={`robot-state robot-state-${tone}`}><i />{metrics.state}</span><small>Simulator</small></div>
        <div><span>OEE</span><strong>{metrics.oeePct}%</strong></div>
        <div><span>Cycle</span><strong>{metrics.cycleTimeSeconds}s</strong></div>
        <div><span>Alarms</span><strong>{metrics.activeAlarms}</strong></div>
      </div>
    </Link>
  );
}
