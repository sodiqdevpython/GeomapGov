import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    bot_token: str
    api_base_url: str

def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    api_base_url = os.getenv("API_BASE_URL", "").strip().rstrip("/")

    if not bot_token:
        raise RuntimeError("BOT_TOKEN topilmadi (.env ni tekshir).")
    if not api_base_url:
        raise RuntimeError("API_BASE_URL topilmadi (.env ni tekshir).")

    return Settings(bot_token=bot_token, api_base_url=api_base_url)
