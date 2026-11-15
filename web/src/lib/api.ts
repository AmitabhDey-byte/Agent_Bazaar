export const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
export async function api<T>(path:string, options:RequestInit={}, token?:string):Promise<T> {
  const response=await fetch(API+path,{...options,headers:{"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`} : {}),...options.headers},cache:"no-store",signal:options.signal??AbortSignal.timeout(25000)});
  const data=await response.json().catch(()=>({detail:"Invalid API response"}));
  if(!response.ok) throw new Error(typeof data.detail==="string"?data.detail:`Request failed (${response.status})`);
  return data as T;
}
export const money=(units:number)=> (units/1e6).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:4});
export const explorer=(hash:string)=>`https://sepolia.basescan.org/tx/${hash}`;
