"""Bound document request bodies before FastAPI's multipart parser runs."""

import anyio
from tempfile import SpooledTemporaryFile
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.ingestion_limits import MULTIPART_OVERHEAD_BYTES, UPLOAD_READ_BYTES


class UploadLimitMiddleware:
    def __init__(self, app: ASGIApp, *, upload_path: str, max_file_bytes: int):
        self.app = app
        self.upload_path = upload_path
        self.max_body_bytes = max_file_bytes + MULTIPART_OVERHEAD_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (scope["type"] != "http" or scope["method"] != "POST"
                or scope["path"].rstrip("/") != self.upload_path):
            await self.app(scope, receive, send)
            return

        async def reject() -> None:
            await JSONResponse(
                {"detail": "Document upload exceeds the request size limit"},
                status_code=413,
            )(scope, receive, send)

        for name, value in scope["headers"]:
            if name.lower() == b"content-length":
                try:
                    length = int(value)
                except ValueError:
                    await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(scope, receive, send)
                    return
                if length > self.max_body_bytes:
                    await reject()
                    return

        # Count actual bytes even when Content-Length is absent or dishonest.
        # Spool to disk after 1 MiB; no unbounded in-memory request buffering.
        async with anyio.wrap_file(SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")) as body:
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                data = message.get("body", b"")
                total += len(data)
                if total > self.max_body_bytes:
                    await reject()
                    return
                await body.write(data)
                if not message.get("more_body", False):
                    break
            await body.seek(0)
            remaining = total

            async def replay():
                nonlocal remaining
                if remaining == 0:
                    return await receive()
                data = await body.read(UPLOAD_READ_BYTES)
                remaining -= len(data)
                return {"type": "http.request", "body": data, "more_body": remaining > 0}

            if total == 0:
                await JSONResponse({"detail": "Empty upload"}, status_code=400)(scope, receive, send)
                return
            await self.app(scope, replay, send)
