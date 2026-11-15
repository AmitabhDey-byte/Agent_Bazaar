"use client";
import {useState} from "react";
import {WagmiProvider,createConfig,http,injected} from "wagmi";
import {baseSepolia} from "wagmi/chains";
import {QueryClient,QueryClientProvider} from "@tanstack/react-query";
import {MotionConfig} from "motion/react";
import {Toaster} from "sonner";
const config=createConfig({chains:[baseSepolia],connectors:[injected()],transports:{[baseSepolia.id]:http()},ssr:true});
export function Providers({children}:{children:React.ReactNode}){
 const [client]=useState(()=>new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:false}}}));
 return <WagmiProvider config={config}><QueryClientProvider client={client}><MotionConfig reducedMotion="user">{children}<Toaster theme="dark" position="bottom-right" richColors /></MotionConfig></QueryClientProvider></WagmiProvider>;
}
