from aiogram import Router
from .start import router as start_router
from .channel import router as channel_router
from .post import router as post_router
from .draft import router as draft_router
from .error import router as error_router


def get_main_router() -> Router:
    """Combine all sub-routers into one root router."""
    root = Router()
    root.include_router(start_router)
    root.include_router(channel_router)
    root.include_router(post_router)
    root.include_router(draft_router)
    root.include_router(error_router)
    return root
