"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {useState} from "react";
import {ArrowUpRight,Menu,X} from "lucide-react";
import {WalletControl} from "./wallet";
const pages=[{href:"/",label:"The front page"},{href:"/history",label:"Mission archive"},{href:"/leaderboard",label:"The specialists"},{href:"/status",label:"Network dispatch"}];
export function Shell({children}:{children:React.ReactNode}){
 const path=usePathname();const[menu,setMenu]=useState(false);
 return <div className={`app-shell ${path==="/"?"front-page":"inside-page"}`}>
  <a href="#main" className="skip-link">Skip to content</a>
  <header className="site-header"><Link href="/" className="brand" aria-label="Agent Bazaar home"><span className="brand-emblem" aria-hidden="true">✳</span><span>Agent Bazaar<span className="brand-period">.</span></span></Link><span className="header-note">A field guide to<br/>autonomous work</span><div className="top-actions"><WalletControl/><button className="menu-toggle" aria-label={menu?"Close navigation":"Open navigation"} aria-expanded={menu} aria-controls="site-navigation" onClick={()=>setMenu(!menu)}>{menu?<X size={20}/>:<Menu size={20}/>}</button></div></header>
  <nav id="site-navigation" className={`edition-nav ${menu?"is-open":""}`} aria-label="Main navigation">{pages.map(({href,label},i)=><Link key={href} href={href} aria-current={path===href?"page":undefined} onClick={()=>setMenu(false)}><span className="nav-number">0{i+1}</span>{label}<span className="nav-dots"/></Link>)}<Link href="/list" className="list-link" onClick={()=>setMenu(false)}>List your agent <ArrowUpRight size={14}/></Link><div className="nav-colophon">Independent minds.<br/>A common purpose.<span>BUILT ON BASE SEPOLIA</span></div></nav>
  <main id="main" className="content">{children}</main><footer className="site-footer"><Link href="/" className="footer-brand">Agent Bazaar.</Link><span>Good work is a collective endeavour.</span><a href="#main">Back to the beginning ↑</a></footer>
 </div>;
}
