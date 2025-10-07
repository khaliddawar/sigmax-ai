from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Allow request bodies up to `max_body_size` bytes (default 5 MB).
    Starlette/uvicorn doesn’t enforce a limit for JSON bodies, but some
    reverse-proxies or earlier middlewares might.  We stream-read the body
    and return 413 if it exceeds the threshold so the client gets a clear
    error instead of silent truncation.
    """

    def __init__(self, app, max_body_size: int = 5 * 1024 * 1024):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        received = 0
        chunks = []
        more_body = True
        while more_body:
            message = await request.receive()
            body_chunk = message.get("body", b"")
            received += len(body_chunk)
            if received > self.max_body_size:
                return Response("Request body too large", status_code=413)
            chunks.append(body_chunk)
            more_body = message.get("more_body", False)
        # Replace request stream with buffered body
        request._body = b"".join(chunks)
        return await call_next(request) 