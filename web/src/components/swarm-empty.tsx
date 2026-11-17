import {AudioLines} from "lucide-react";

export function SwarmEmpty(){
 return <div className="swarm swarm-empty" aria-label="Orchestrator awaiting registered agents">
  <div className="agent-node center">
   <div className="node-icon"><AudioLines size={25}/></div>
   <div className="node-label">Orchestrator</div>
   <div className="node-meta mono">PLAN · AUCTION · VERIFY</div>
  </div>
  <div className="graph-empty mono">Registered agents appear here when the network connects.</div>
 </div>;
}
