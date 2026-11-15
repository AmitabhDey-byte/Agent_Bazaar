import type {NextConfig} from "next";
const config:NextConfig={reactStrictMode:true,poweredByHeader:false,outputFileTracingRoot:process.cwd(),distDir:process.env.NODE_ENV==="development"?".next-dev":".next",async headers(){return[{source:"/(.*)",headers:[{key:"X-Content-Type-Options",value:"nosniff"},{key:"Referrer-Policy",value:"strict-origin-when-cross-origin"},{key:"X-Frame-Options",value:"DENY"},{key:"Permissions-Policy",value:"camera=(), geolocation=(), microphone=(self)"}]}]}};
export default config;
