import { registerDefinitionForRobot } from "../data/registerDefinitions";
import "./ClientRegisterData.css";

export default function ClientRegisterData({ robot }) {
  const schema = registerDefinitionForRobot(robot);
  if (!schema) return null;

  return <article className="featured-intel-card featured-registers">
    <header><h2>Client Register Data</h2><span>REGISTER DEFINITIONS · NOT LIVE VALUES</span></header>
    <div className="featured-register-note">
      <strong>{schema.cellName}</strong>
      <span>Definitions from the client workbook sheet “{schema.sourceSheet}”. Current values remain unavailable until a FANUC register connection populates <code>registers[index]</code>.</span>
    </div>
    <div className="featured-register-table" role="table" aria-label={`${schema.cellName} client register definitions`}>
      {schema.registers.map((register) => <div className="featured-register-row" role="row" key={register.index}>
        <b>R[{register.index}]</b>
        <span>{register.label}{register.unit ? ` (${register.unit})` : ""}<small>{register.group}</small></span>
        <strong>Awaiting live register value</strong>
      </div>)}
    </div>
  </article>;
}
