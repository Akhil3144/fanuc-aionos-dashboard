import "./AITag.css";

export default function AITag({ label = "ANALYTICS / AI" }) {
  return <span className="ai-tag" title="Analytics / AI-assisted insight derived from available robot evidence.">{label}</span>;
}
