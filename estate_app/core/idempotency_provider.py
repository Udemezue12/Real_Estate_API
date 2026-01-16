import uuid
from fastapi import Request


async def get_idem_key(request: Request) -> str:
    key = request.headers.get("Idempotency-Key")
    return key or str(uuid.uuid4())
