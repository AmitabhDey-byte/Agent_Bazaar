"use client";
import {useQuery} from "@tanstack/react-query";
import {api,explorer} from "@/lib/api";
import type{Run} from "@/lib/types";
import {Share2} from "lucide-react";
export function SharedRun({token}:{token:string}){const run=useQuery({queryKey:["public-run",token],queryFn:()=>api<Run>(`/public/${encodeURIComponent(token)}`)});if(!run.data)return <div className="page-card empty-panel"><Share2/><h2>{run.isLoading?"Opening shared mission…":"Shared mission unavailable"}</h2><p>{run.isError?"The link may have expired or the API is unreachable.":"Loading the saved outcome and receipts."}</p></div>;return <><div className="eyebrow">SHARED MISSION / {run.data.status}</div><h1>{run.data.goal}</h1><section className="answer"><pre>{run.data.answer??"No final synthesis is available for this run."}</pre></section><div className="page-card mt-6"><h2>On-chain receipts</h2>{run.data.events?.filter(e=>typeof e.data.tx_hash==="string").map(e=><div className="trace-line" key={e.id}><a href={explorer(String(e.data.tx_hash))} target="_blank" rel="noreferrer" className="lime">{e.type} · {String(e.data.tx_hash).slice(0,18)}… ↗</a></div>)}</div></>}
