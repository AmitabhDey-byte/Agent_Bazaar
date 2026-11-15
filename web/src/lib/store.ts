"use client";
import {create} from "zustand";
import {createJSONStorage,persist} from "zustand/middleware";
type SessionState={token:string;cap:number;wallet:string;setSession:(token:string,cap:number,wallet:string)=>void;clear:()=>void};
export const useSession=create<SessionState>()(persist(set=>({token:"",cap:0,wallet:"",setSession:(token,cap,wallet)=>set({token,cap,wallet}),clear:()=>set({token:"",cap:0,wallet:""})}),{name:"agent-bazaar-session",storage:createJSONStorage(()=>sessionStorage)}));
