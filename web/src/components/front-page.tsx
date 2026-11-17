import {Dashboard} from "./dashboard";
import {ScrollJourney} from "./scroll-journey";

export function FrontPage(){return <>
 <ScrollJourney/>
 <section id="mission" className="mission-section journey-destination" aria-label="Mission workspace">
  <div className="chapter-label"><span>THE NEXT CHAPTER IS YOURS</span><span>FROM THE FIELD GUIDE TO THE FIELD</span><span>↓</span></div>
  <Dashboard embedded/>
 </section>
 </>;}
