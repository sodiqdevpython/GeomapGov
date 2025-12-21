import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.db import BotDB
from app.api import ApiClient
from app.handlers.init import get_routers

async def main():
    settings = get_settings()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    db = BotDB()
    await db.init()

    api = ApiClient(settings.api_base_url)

    # dependencies (oddiy usul: dp["db"]=..., handlerda parametr sifatida ishlatamiz)
    dp["db"] = db
    dp["api"] = api

    for r in get_routers():
        dp.include_router(r)

    await dp.start_polling(bot, db=db, api=api)

if __name__ == "__main__":
    asyncio.run(main())
