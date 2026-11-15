"use client";
import {Button} from "@/components/ui/button";
export default function ErrorBoundary({reset}:{error:Error&{digest?:string};reset:()=>void}){return <div className="page-card empty-panel"><h1>Something interrupted this view.</h1><p>Your persisted runs and payment receipts remain on the server.</p><Button onClick={reset}>Try again</Button></div>}
