export type Agent = { id:number; owner:string; pay_to:string; price:number; endpoint:string; capability:string; reputation:number; active:boolean };
export type RunEvent = { id:number; type:string; data:Record<string,unknown>; created_at?:string };
export type Run = { id:string; goal:string; status:string; created_at:string; answer?:string; results?:Record<string,{output?:string;verified?:boolean;error?:string;image?:string}>; events?:RunEvent[]; payments?:{id:string;agent_id:number;amount:number;status:string;tx_hash?:string;escrow_id?:string}[] };
export type Health = { ok:boolean; network:string; checks:Record<string,{ok:boolean;detail:unknown}>; agents?:{id:number;capability:string;ok:boolean}[] };
