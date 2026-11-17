import {NextRequest,NextResponse} from "next/server";
export function middleware(request:NextRequest){
 const nonce=btoa(crypto.randomUUID());
 const apiOrigin=new URL(process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000").origin;
 const dev=process.env.NODE_ENV==="development";
 const policy=["default-src 'self'",`script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev?" 'unsafe-eval'":""}`,"style-src 'self' 'unsafe-inline'",`connect-src 'self' ${apiOrigin} https://sepolia.base.org${dev?" ws://localhost:3000 ws://127.0.0.1:3000":""}`,"img-src 'self' data: blob: https:","font-src 'self'","object-src 'none'","base-uri 'self'","frame-ancestors 'none'","form-action 'self'"].join("; ");
 const headers=new Headers(request.headers);headers.set("x-nonce",nonce);headers.set("Content-Security-Policy",policy);
 const response=NextResponse.next({request:{headers}});response.headers.set("Content-Security-Policy",policy);return response;
}
// Vercel Services cannot deploy Edge output. Node middleware is stable in Next 15.5.
export const config={runtime:"nodejs",matcher:[{source:"/((?!api|_next/static|_next/image|favicon.ico).*)",missing:[{type:"header",key:"next-router-prefetch"},{type:"header",key:"purpose",value:"prefetch"}]}]};
