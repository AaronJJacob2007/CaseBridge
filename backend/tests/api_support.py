"""Exercise the real FastAPI ASGI app without adding an HTTP client package."""
import asyncio
import json

from sqlalchemy import select

from backend.main import app
from backend.models import User


class DatabaseApi:
    def __init__(self, db):
        self.db = db

    def user(self, name):
        return self.db.scalar(select(User).where(User.name == name)).id

    def request(self, method, path, data=None, user=None, *, raw=False):
        async def run():
            body = json.dumps(data).encode() if data is not None else b""
            headers = [(b"content-type", b"application/json")]
            if user is not None:
                headers.append((b"x-user-id", str(user).encode()))
            scope = {
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": method, "scheme": "http", "path": path,
                "raw_path": path.encode(), "query_string": b"", "root_path": "",
                "headers": headers, "server": ("test", 80), "client": ("127.0.0.1", 1234),
            }
            messages = []

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            async def send(message):
                messages.append(message)

            await app(scope, receive, send)
            status = next(message["status"] for message in messages if message["type"] == "http.response.start")
            content = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
            if raw:
                response_headers = next(message["headers"] for message in messages if message["type"] == "http.response.start")
                return status, content.decode("utf-8"), {key.decode(): value.decode() for key, value in response_headers}
            return status, json.loads(content)
        return asyncio.run(run())
