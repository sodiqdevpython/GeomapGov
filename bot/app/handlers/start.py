import aiohttp
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..states import Registration
from ..keyboards import menu_kb, phone_request_kb
from ..db import BotDB
from ..api import ApiClient, now_iso, ApiError

router = Router()


@router.message(F.text.in_({"/start", "/restart"}))
async def start(message: Message, state: FSMContext, db: BotDB):
    await state.clear()

    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)

    if user:
        await message.answer("✅ Xush kelibsiz!", reply_markup=menu_kb())
        return

    await message.answer("Assalomu alaykum! Ro‘yxatdan o‘tish uchun ismingizni kiriting:")
    await state.set_state(Registration.waiting_first_name)


@router.message(Registration.waiting_first_name, F.text)
async def reg_first_name(message: Message, state: FSMContext):
    first_name = (message.text or "").strip()
    if len(first_name) < 2:
        await message.answer("Ism juda qisqa. Qaytadan kiriting:")
        return

    await state.update_data(first_name=first_name)
    await message.answer("Familiyangizni kiriting:")
    await state.set_state(Registration.waiting_last_name)


@router.message(Registration.waiting_last_name, F.text)
async def reg_last_name(message: Message, state: FSMContext):
    last_name = (message.text or "").strip()
    if len(last_name) < 2:
        await message.answer("Familiya juda qisqa. Qaytadan kiriting:")
        return

    await state.update_data(last_name=last_name)
    await message.answer(
        "📱 Telefon raqamingizni yuboring (pastdagi tugmani bosing):",
        reply_markup=phone_request_kb()
    )
    await state.set_state(Registration.waiting_phone)


@router.message(Registration.waiting_phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    contact = message.contact

    # Faqat o'ziniki bo'lsin (boshqa odam contact yuborsa o‘tmaydi)
    if not contact or contact.user_id != message.from_user.id:
        await message.answer("❌ Iltimos, faqat o‘zingizning telefon raqamingizni yuboring.")
        return

    phone_number = (contact.phone_number or "").replace(" ", "")

    data = await state.get_data()
    telegram_id = message.from_user.id

    async with aiohttp.ClientSession() as session:
        try:
            resp = await api.auth_telegram(
                session=session,
                telegram_id=telegram_id,
                first_name=data["first_name"],
                last_name=data["last_name"],
                phone_number=phone_number,
            )
        except ApiError as e:
            await message.answer(f"❌ Ro‘yxatdan o‘tishda xatolik: {e}\nQayta urinib ko‘ring.")
            return

    access = resp["tokens"]["access"]
    refresh = resp["tokens"]["refresh"]

    await db.upsert_user_tokens(
        telegram_id=telegram_id,
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone_number=phone_number,
        access_token=access,
        refresh_token=refresh,
        updated_at_iso=now_iso(),
    )

    await state.clear()
    await message.answer("✅ Ro‘yxatdan o‘tdingiz! Menyu:", reply_markup=menu_kb())


@router.message(Registration.waiting_first_name)
@router.message(Registration.waiting_last_name)
@router.message(Registration.waiting_phone)
async def reg_text_only(message: Message):
    await message.answer("Iltimos, matn ko‘rinishida yuboring.")

@router.message(Registration.waiting_phone)
async def reg_phone_only_button(message: Message):
    await message.answer("❗ Telefon raqamni faqat pastdagi tugma orqali yuboring.")

