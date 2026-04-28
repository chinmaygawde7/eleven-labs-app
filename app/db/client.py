from supabase import create_client, Client
from app.config import Config

_service_client: Client | None = None


def get_service_client() -> Client:
    """
    Admin client — bypasses Row Level Security.
    Use ONLY in server-side code (scheduler, cloning).
    Never send this key to the browser.
    """
    global _service_client
    if _service_client is None:
        _service_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _service_client


def get_user_client(access_token: str) -> Client:
    """
    User-scoped client — respects Row Level Security.
    Use in blueprint routes where the logged-in user
    should only see their own rows.
    """
    client = create_client(
        Config.SUPABASE_URL,
        Config.SUPABASE_ANON_KEY,
    )
    client.auth.set_session(access_token, "")
    return client