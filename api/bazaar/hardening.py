"""Pure ASGI guards preserve streaming and bound request bodies before paid work."""

import json
import logging

from starlette.responses import JSONResponse


class SecurityMiddleware:
    def __init__(self, app, store, max_body=64000):
        self.app, self.store, self.max_body = app, store, max_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        client = (scope.get("client") or ("unknown",))[0]
        try:
            if not await self.store.rate_limit(f"http:{client}", 180, 60):
                return await JSONResponse({"detail": "Rate limit exceeded"}, 429)(scope, receive, send)
        except Exception as error:
            logging.getLogger("bazaar").warning(
                json.dumps({"event": "rate_limit_unavailable", "error": type(error).__name__})
            )
            # Paid work fails closed. Health remains inspectable during Redis outages.
            if scope["method"] != "GET":
                return await JSONResponse({"detail": "Rate limiter unavailable"}, 503)(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_body:
                return await JSONResponse({"detail": "Request body exceeds 64 KB"}, 413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([(b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"no-referrer")])
                if path not in ("/docs", "/redoc"):
                    headers.append((b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, bounded_receive, secure_send)
