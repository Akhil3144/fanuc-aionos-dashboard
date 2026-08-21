import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import AskMyRobot from "../components/AskMyRobot";
import RobotCard from "../components/RobotCard";
import { featuredRobots, registryApplications, robotRegistry, ROBOT_REGISTRY_SOURCE } from "../data/robotRegistry";
import { currentMetricsFor, loadOpenHouseCurrent, simulatorMetricsFor } from "../services/fleetSimulator";
import "./FleetPage.css";

export default function FleetPage() {
  const [search, setSearch] = useState("");
  const [application, setApplication] = useState("ALL");
  const [status, setStatus] = useState("ALL");
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const [currentById, setCurrentById] = useState({});

  useEffect(() => {
    loadOpenHouseCurrent()
      .then((items) => setCurrentById(Object.fromEntries(items.map((item) => [item.robot_id, item]))))
      .catch(console.error);
  }, []);

  const robots = useMemo(() => robotRegistry.map((robot) => ({
    robot,
    metrics: currentMetricsFor(currentById[robot.id], robot) || simulatorMetricsFor(robot),
  })), [currentById]);
  const filtered = robots.filter(({ robot, metrics }) => {
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || [robot.id, robot.serialNo, robot.model, robot.application, robot.ipAddress].some((value) => String(value || "").toLowerCase().includes(query));
    return matchesSearch && (application === "ALL" || robot.application === application) && (status === "ALL" || metrics.state === status) && (!featuredOnly || robot.featured);
  });

  return (
    <div className="fleet-page">
      <header className="fleet-page-header">
        <Link to="/" className="fleet-brand">FANUC <span>×</span> AIonOS</Link>
        <div><p>Open House 2026</p><h1>Robot Fleet</h1><span>Fleet configuration and operational intelligence</span></div>
        <div className="fleet-mode"><span><i /> System Ready</span><span>Telemetry · Simulator</span><span>Read Only</span></div>
      </header>

      <main className="fleet-page-content">
        <section className="fleet-summary" aria-label="Fleet summary">
          <article><span>Total robots</span><strong>{robotRegistry.length}</strong><small>{ROBOT_REGISTRY_SOURCE}</small></article>
          <article><span>Applications</span><strong>{registryApplications.length}</strong><small>Distinct specified applications</small></article>
          <article><span>Featured robots</span><strong>{featuredRobots.length}</strong><small>Workbook-highlighted cells</small></article>
          <article><span>Data mode</span><strong className="fleet-summary-mode">Simulator</strong><small>Operational analytics</small></article>
        </section>

        <section className="fleet-controls" aria-label="Search and filters">
          <label className="fleet-search"><span>Search fleet</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Model, application, IP or ID" /></label>
          <label><span>Application</span><select value={application} onChange={(event) => setApplication(event.target.value)}><option value="ALL">All applications</option>{registryApplications.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span>Status</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="ALL">All states</option>{["RUNNING", "READY", "IDLE", "FAULTED"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="featured-toggle"><input type="checkbox" checked={featuredOnly} onChange={(event) => setFeaturedOnly(event.target.checked)} /><span>Featured only</span></label>
        </section>

        <div className="fleet-results"><span>Showing {filtered.length} of {robotRegistry.length} robots</span><span>Open House 2026 · Telemetry: Simulator</span></div>
        <section className="robot-grid">{filtered.map(({ robot, metrics }) => <RobotCard key={robot.id} robot={robot} metrics={metrics} />)}</section>
        {!filtered.length && <div className="fleet-empty">No robots match the current filters.</div>}

        <section className="fleet-ask"><div className="fleet-ask-title"><p>Fleet intelligence</p><h2>Ask My Robot · All Robots</h2></div><AskMyRobot scope="FLEET" robots={robotRegistry} registry={robotRegistry} /></section>
      </main>
      <footer className="fleet-footer"><span>Open House 2026 Robot Fleet</span><span>Telemetry: Simulator · Read Only</span></footer>
    </div>
  );
}
