from typing import Optional
from supabase import create_client, Client
from app.config import Config

_service_client: Optional[Client] = None


def get_service_client() -> Client:
    global _service_client
    if _service_client is None:
        _service_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _service_client


def get_user_client(access_token: str) -> Client:
    client = create_client(
        Config.SUPABASE_URL,
        Config.SUPABASE_ANON_KEY,
    )
    # Compatible with supabase-py v1 and v2
    try:
        client.auth.set_session(access_token, "")
    except Exception:
        pass
    return client