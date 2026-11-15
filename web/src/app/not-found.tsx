import Link from "next/link";
export default function NotFound(){return <div className="empty-panel"><h1>This mission is off the map.</h1><p>The requested page does not exist.</p><Link className="lime" href="/">Return to mission control ↗</Link></div>}
