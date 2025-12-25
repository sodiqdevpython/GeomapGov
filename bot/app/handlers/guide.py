import aiohttp
from aiogram import Router, F
from aiogram.types import Message

from ..db import BotDB
from ..api import ApiClient, ApiError, now_iso

router = Router()


async def ensure_fresh_token(db: BotDB, api: ApiClient, telegram_id: int) -> str:
    user = await db.get_user(telegram_id)
    if not user:
        return ""

    async with aiohttp.ClientSession() as session:
        auth = await api.auth_telegram(
            session=session,
            telegram_id=telegram_id,
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone_number=user["phone_number"],
        )

    access = auth["tokens"]["access"]
    refresh = auth["tokens"]["refresh"]

    await db.upsert_user_tokens(
        telegram_id=telegram_id,
        first_name=user["first_name"],
        last_name=user["last_name"],
        phone_number=user["phone_number"],
        access_token=access,
        refresh_token=refresh,
        updated_at_iso=now_iso(),
    )
    return access


@router.message(F.text.startswith("Ishlatish bo‘yicha qo‘llanma"))
async def guide(message: Message, db: BotDB, api: ApiClient):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.")
        return

    async def fetch(access_token: str):
        async with aiohttp.ClientSession() as session:
            return await api.guide(session, access_token)

    try:
        data = await fetch(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            try:
                new_access = await ensure_fresh_token(db, api, telegram_id)
                data = await fetch(new_access)
            except Exception as e2:
                await message.answer(f"❌ Token yangilanmadi: {e2}")
                return
        else:
            await message.answer(f"❌ Xatolik: {e}")
            return

    title = data.get("title", "Qo‘llanma")
    steps = data.get("steps") or []
    text = f"📘 {title}\n\n" + "\n".join(steps)
    await message.answer(text)
