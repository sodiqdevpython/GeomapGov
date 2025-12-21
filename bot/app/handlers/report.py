import aiohttp
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..states import ReportCreate
from ..keyboards import menu_kb, cancel_kb, media_kb, location_kb, confirm_kb
from ..db import BotDB
from ..api import ApiClient, ApiError, now_iso
from ..utils import guess_content_type, safe_filename
from .my_reports import maps_url

router = Router()

MAX_FILES = 10


def _init_media_state():
    return {"files": []}  # [{file_id, filename, content_type}]


@router.message(F.text.startswith("1."))
async def report_start(message: Message, state: FSMContext, db: BotDB):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.")
        return

    await state.clear()
    await state.set_state(ReportCreate.waiting_description)
    await state.update_data(media=_init_media_state())

    await message.answer("Muammoni matn ko‘rinishida yozing:", reply_markup=cancel_kb())


@router.message(ReportCreate.waiting_description, F.text == "❌ Bekor qilish")
async def cancel_from_description(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


@router.message(ReportCreate.waiting_description, F.text)
async def report_got_description(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("Matn juda qisqa. Iltimos muammoni batafsilroq yozing.", reply_markup=cancel_kb())
        return

    await state.update_data(description=text)
    await state.set_state(ReportCreate.collecting_media)

    await message.answer(
        "Endi xohlasangiz rasm/video/ovoz/audio/pdf/file yuboring.\n"
        "Tayyor bo‘lsangiz: ✅ Joylashuv yuborish ni bosing.\n\n",
        reply_markup=media_kb()
    )


@router.message(ReportCreate.collecting_media, F.text == "❌ Bekor qilish")
async def report_cancel_media(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


@router.message(ReportCreate.collecting_media, F.text == "✅ Joylashuv yuborish")
async def report_ask_location(message: Message, state: FSMContext):
    await state.set_state(ReportCreate.waiting_location)
    await message.answer(
        "Muammo joylashuvini yuboring.",
        reply_markup=location_kb()
    )


def _append_file(state_files: list, file_id: str, filename: str, content_type: str):
    state_files.append({"file_id": file_id, "filename": filename, "content_type": content_type})


@router.message(ReportCreate.collecting_media, F.photo)
async def report_collect_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    photo = message.photo[-1]
    _append_file(files, photo.file_id, safe_filename(f"photo_{len(files)+1}.jpg"), "image/jpeg")
    await state.update_data(media=media)
    await message.answer(f"✅ Rasm qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.video)
async def report_collect_video(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    v = message.video
    filename = safe_filename(v.file_name or f"video_{len(files)+1}.mp4")
    _append_file(files, v.file_id, filename, v.mime_type or "video/mp4")
    await state.update_data(media=media)
    await message.answer(f"✅ Video qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.voice)
async def report_collect_voice(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    v = message.voice
    _append_file(files, v.file_id, safe_filename(f"voice_{len(files)+1}.ogg"), v.mime_type or "audio/ogg")
    await state.update_data(media=media)
    await message.answer(f"✅ Ovozli xabar qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.audio)
async def report_collect_audio(message: Message, state: FSMContext):
    # ✅ MUHIM: audio file (music) uchun handler
    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    a = message.audio
    filename = safe_filename(a.file_name or f"audio_{len(files)+1}.mp3")
    _append_file(files, a.file_id, filename, a.mime_type or guess_content_type(filename))
    await state.update_data(media=media)
    await message.answer(f"✅ Audio qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.document)
async def report_collect_document(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    d = message.document
    filename = safe_filename(d.file_name or f"file_{len(files)+1}")
    _append_file(files, d.file_id, filename, d.mime_type or guess_content_type(filename))
    await state.update_data(media=media)
    await message.answer(f"✅ Fayl qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.waiting_location, F.text == "❌ Bekor qilish")
async def report_cancel_location(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


@router.message(ReportCreate.waiting_location, F.location)
async def report_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    files = (data.get("media") or _init_media_state())["files"]

    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    link = maps_url(lat, lon) if (lat is not None and lon is not None) else ""
    await state.update_data(latitude=lat, longitude=lon)

    preview_text = (
        "📄 Murojaatni tasdiqlash\n\n"
        f"📝 Matn:\n{data.get('description','')}\n\n"
        f"📎 Fayllar soni: {len(files)}\n"
        f"📍 Joylashuv: {link}\n\n"
        "Agar hammasi to‘g‘ri bo‘lsa: ✅ Ha, tanishib chiqdim roziman\n"
        "Aks holda: ❌ Bekor qilish"
    )

    await state.set_state(ReportCreate.confirm)
    await message.answer(preview_text, reply_markup=confirm_kb())


@router.message(ReportCreate.confirm, F.text == "❌ Bekor qilish")
async def report_cancel_confirm(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi. Saqlanmadi.", reply_markup=menu_kb())


@router.message(ReportCreate.confirm, F.text == "✅ Ha, tanishib chiqdim roziman")
async def report_submit_confirmed(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await state.clear()
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.")
        return

    data = await state.get_data()
    description = data.get("description", "")
    lat = float(data.get("latitude"))
    lon = float(data.get("longitude"))
    files_meta = (data.get("media") or _init_media_state())["files"]

    # User “qotib qoldi” deb o‘ylamasin:
    await message.answer("⏳ Yuborilyapti… iltimos biroz kuting.")

    # Fayllarni faqat Roziman bosilganda download qilamiz
    tg_files = []
    for item in files_meta:
        file_id = item["file_id"]
        filename = item["filename"]
        ctype = item["content_type"]

        f = await message.bot.get_file(file_id)
        stream = BytesIO()
        await message.bot.download_file(f.file_path, stream)
        tg_files.append((filename, stream.getvalue(), ctype))

    async def submit(access_token: str):
        async with aiohttp.ClientSession() as session:
            return await api.create_report(
                session=session,
                access_token=access_token,
                description=description,
                latitude=lat,
                longitude=lon,
                files=tg_files,
            )

    try:
        created = await submit(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            async with aiohttp.ClientSession() as session2:
                auth = await api.auth_telegram(
                    session=session2,
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
            created = await submit(access)
        else:
            await message.answer(f"❌ Murojaat yuborilmadi: {e}", reply_markup=menu_kb())
            await state.clear()
            return

    await state.clear()
    await message.answer(
        f"✅ Murojaat saqlandi!\nID: {created.get('id')}\nStatus: {created.get('status')}",
        reply_markup=menu_kb()
    )
