from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_user_key(request: Request) -> str:
    # keyed by authenticated user if available, otherwise falls back to IP
    user = getattr(request.state, "user", None)
    return f"user:{user.id}" if user else get_remote_address(request)


limiter = Limiter(key_func=get_user_key)