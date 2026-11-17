"""Local ASGI runner using a Psycopg-compatible event loop on Windows."""

import asyncio
import sys

import uvicorn


def selector_loop():
    return asyncio.SelectorEventLoop()


if __name__ == "__main__":
    uvicorn.run(
        "index:app", host="127.0.0.1", port=8000, loop="dev:selector_loop" if sys.platform == "win32" else "asyncio"
    )
