from fastapi import APIRouter

from app.config import get_settings_singleton

router = APIRouter(tags=["health"])
settings = get_settings_singleton()
APP_NAME = getattr(settings, "APP_NAME", "t4too_fastapi")


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": APP_NAME}


@router.get("/ai/principles")
def ai_principles() -> dict[str, list[str]]:
    return {
        "principles": [
            "AI-first: workflows begin with AI proposals.",
            "AI-internal: reasoning and confidence are stored with each draft.",
            "AI-inherited: each action keeps a chain from source transaction to posted ledger.",
            "Human approval is mandatory before posting.",
        ]
    }

