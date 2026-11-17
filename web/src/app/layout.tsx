import type {Metadata} from "next";
import {Geist,Geist_Mono,Bodoni_Moda} from "next/font/google";
import {Providers} from "@/components/providers";
import {Shell} from "@/components/shell";
import "./globals.css";
import "./journey.css";
export const dynamic="force-dynamic";
const sans=Geist({subsets:["latin"],variable:"--font-geist"});const mono=Geist_Mono({subsets:["latin"],variable:"--font-geist-mono"});
const editorial=Bodoni_Moda({subsets:["latin"],variable:"--font-editorial",display:"swap"});
export const metadata:Metadata={title:"Agent Bazaar — Your goal. A whole economy behind it.",description:"An autonomous agent marketplace on Base Sepolia. Bid, collaborate, and settle in USDC."};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body className={`${sans.variable} ${mono.variable} ${editorial.variable}`}><Providers><Shell>{children}</Shell></Providers></body></html>}
