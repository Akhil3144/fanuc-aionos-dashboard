import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import FleetExecutiveCards from "../components/FleetExecutiveCards";
import FleetShowcaseVideo from "../components/FleetShowcaseVideo";
import { featuredRobots, registryApplications, robotRegistry, ROBOT_REGISTRY_SOURCE } from "../data/robotRegistry";
import { fleetSummarySimulator, loadFleetSummarySimulator } from "../services/fleetSummarySimulator";
import "./HomePage.css";

function HomePage() {
  const [generatedSummary, setGeneratedSummary] = useState(fleetSummarySimulator);
  useEffect(() => { loadFleetSummarySimulator().then(setGeneratedSummary).catch(console.error); }, []);
  const fleetExecutiveSummary = useMemo(() => ({
    ...generatedSummary,
    totalRobots: robotRegistry.length,
    applicationTypes: registryApplications.length,
    featuredRobots: featuredRobots.length,
  }), [generatedSummary]);
  return (
    <div className="home-page">
      <header className="home-header">
        <div className="home-brand">FANUC <span>×</span> AIonOS</div>
        <div className="home-heading">
          <p>MAIN DASHBOARD · LEVEL 01</p>
          <h1>Exhibition Cell Intelligence</h1>
          <span>Overall Performance of All {robotRegistry.length} Robots</span>
        </div>
        <div className="home-status" aria-label="System status">
          <span><i /> System Ready</span>
          <span>Telemetry · Simulator</span>
          <span>Read Only</span>
        </div>
      </header>

      <main className="home-content">
        <section className="home-section" aria-labelledby="fleet-intelligence-title">
          <div className="section-heading">
            <div>
              <p>Executive overview</p>
              <h2 id="fleet-intelligence-title">Fleet intelligence</h2>
            </div>
            <span>{robotRegistry.length} registered assets</span>
          </div>
          <div className="home-data-source"><span>Robot Registry · {ROBOT_REGISTRY_SOURCE}</span><span>Telemetry · Simulator</span></div>
          <FleetExecutiveCards summary={fleetExecutiveSummary} />
        </section>

        <FleetShowcaseVideo />

        <section className="home-navigation" aria-labelledby="explore-title">
          <div className="section-heading">
            <div>
              <p>Operations</p>
              <h2 id="explore-title">Explore fleet intelligence</h2>
            </div>
          </div>
          <Link className="operations-cta" to="/fleet"><strong>Explore all robots</strong><span>→</span></Link>
        </section>
      </main>

      <footer className="home-footer">
        <strong>FANUC <span>×</span> AIonOS</strong>
        <p>Exhibition Cell Intelligence Platform</p>
      </footer>
    </div>
  );
}

export default HomePage;
